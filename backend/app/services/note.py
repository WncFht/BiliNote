import json
import logging
import os
import re
from dataclasses import asdict
from pathlib import Path
from threading import Event, Thread
from typing import Callable, List, Optional, Tuple, Union, Any

from fastapi import HTTPException
from pydantic import HttpUrl
from dotenv import load_dotenv

from app.downloaders.base import Downloader
from app.downloaders.bilibili_downloader import BilibiliDownloader
from app.downloaders.douyin_downloader import DouyinDownloader
from app.downloaders.local_downloader import LocalDownloader
from app.downloaders.youtube_downloader import YoutubeDownloader
from app.db.video_task_dao import delete_task_by_video, insert_video_task
from app.enmus.exception import NoteErrorEnum, ProviderErrorEnum
from app.enmus.task_status_enums import TaskStatus
from app.enmus.note_enums import DownloadQuality
from app.exceptions.note import NoteError
from app.exceptions.provider import ProviderError
from app.gpt.base import GPT
from app.gpt.gpt_factory import GPTFactory
from app.models.audio_model import AudioDownloadResult
from app.models.gpt_model import GPTSource
from app.models.model_config import ModelConfig
from app.models.notes_model import AudioDownloadResult, NoteResult
from app.models.transcriber_model import TranscriptResult, TranscriptSegment
from app.services.constant import SUPPORT_PLATFORM_MAP
from app.services.provider import ProviderService
from app.transcriber.base import Transcriber
from app.transcriber.transcriber_provider import get_transcriber, _transcribers
from app.utils.note_helper import normalize_math_delimiters, replace_content_markers
from app.utils.status_code import StatusCode
from app.utils.video_helper import generate_screenshot
from app.utils.video_reader import VideoReader

# ------------------ 环境变量与全局配置 ------------------

# 从 .env 文件中加载环境变量
load_dotenv()

# 后端 API 地址与端口（若有需要可以在代码其他部分使用 BACKEND_BASE_URL）
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost")
BACKEND_PORT = os.getenv("BACKEND_PORT", "8483")
BACKEND_BASE_URL = f"{API_BASE_URL}:{BACKEND_PORT}"

# 输出目录（用于缓存音频、转写、Markdown 文件，以及存储截图）
NOTE_OUTPUT_DIR = Path(os.getenv("NOTE_OUTPUT_DIR", "note_results"))
NOTE_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
IMAGE_OUTPUT_DIR = os.getenv("OUT_DIR", "./static/screenshots")
# 图片基础 URL（用于生成 Markdown 中的图片链接，需前端静态目录对应）
IMAGE_BASE_URL = os.getenv("IMAGE_BASE_URL", "/static/screenshots")
OPERATION_HEARTBEAT_SECONDS = float(os.getenv("NOTE_PROGRESS_HEARTBEAT_SECONDS", "15"))

# 日志配置
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class NoteGenerator:
    """
    NoteGenerator 用于执行视频/音频下载、转写、GPT 生成笔记、插入截图/链接、
    以及将任务信息写入状态文件与数据库等功能。
    """

    def __init__(self):
        self.model_size: str = "base"
        self.device: Optional[str] = None
        self.transcriber_type: str = os.getenv("TRANSCRIBER_TYPE", "fast-whisper")
        self.transcriber: Transcriber = self._init_transcriber()
        self.video_path: Optional[Path] = None
        self.video_img_urls=[]
        self.progress_callback: Optional[Callable[[str, Optional[str]], None]] = None
        logger.info("NoteGenerator 初始化完成")


    # ---------------- 公有方法 ----------------

    def generate(
        self,
        video_url: Union[str, HttpUrl],
        platform: str,
        quality: DownloadQuality = DownloadQuality.medium,
        task_id: Optional[str] = None,
        model_name: Optional[str] = None,
        provider_id: Optional[str] = None,
        link: bool = False,
        screenshot: bool = False,
        _format: Optional[List[str]] = None,
        style: Optional[str] = None,
        extras: Optional[str] = None,
        output_path: Optional[str] = None,
        video_understanding: bool = False,
        video_interval: int = 0,
        grid_size: Optional[List[int]] = None,
        progress_callback: Optional[Callable[[str, Optional[str]], None]] = None,
    ) -> NoteResult | None:
        """
        主流程：按步骤依次下载、转写、GPT 总结、截图/链接处理、存库、返回 NoteResult。

        :param video_url: 视频或音频链接
        :param platform: 平台名称，对应 SUPPORT_PLATFORM_MAP 中的键
        :param quality: 下载音频的质量枚举
        :param task_id: 用于标识本次任务的唯一 ID，亦用于状态文件和缓存文件命名
        :param model_name: GPT 模型名称
        :param provider_id: 模型供应商 ID
        :param link: 是否在笔记中插入视频片段链接
        :param screenshot: 是否在笔记中替换 Screenshot 标记为图片
        :param _format: 包含 'link' 或 'screenshot' 等字符串的列表，决定后续处理
        :param style: GPT 生成笔记的风格
        :param extras: 额外参数，传递给 GPT
        :param output_path: 下载输出目录（可选）
        :param video_understanding: 是否需要视频拼图理解（生成缩略图）
        :param video_interval: 视频帧截取间隔（秒），仅在 video_understanding 为 True 时生效
        :param grid_size: 生成缩略图时的网格大小，如 [3, 3]
        :return: NoteResult 对象，包含 markdown 文本、转写结果和音频元信息
        """
        if grid_size is None:
            grid_size = []

        self.progress_callback = progress_callback
        try:
            logger.info(f"开始生成笔记 (task_id={task_id})")
            self._update_status(task_id, TaskStatus.PARSING)
            self.video_path = None
            self.video_img_urls = []

            # 获取下载器与 GPT 实例

            downloader = self._get_downloader(platform)
            gpt = self._get_gpt(model_name, provider_id)

            # 缓存文件路径
            audio_cache_file = NOTE_OUTPUT_DIR / f"{task_id}_audio.json"
            transcript_cache_file = NOTE_OUTPUT_DIR / f"{task_id}_transcript.json"
            markdown_cache_file = NOTE_OUTPUT_DIR / f"{task_id}_markdown.md"
            print(audio_cache_file)
            need_video = screenshot or video_understanding
            if platform == "bilibili":
                audio_meta = self._get_bilibili_metadata(
                    downloader=downloader,
                    video_url=video_url,
                    audio_cache_file=audio_cache_file,
                    status_phase=TaskStatus.DOWNLOADING,
                    output_path=output_path,
                )
                if need_video:
                    self._prepare_video_assets(
                        downloader=downloader,
                        video_url=video_url,
                        task_id=task_id,
                        output_path=output_path,
                        video_interval=video_interval,
                        grid_size=grid_size,
                    )
                transcript, audio_meta = self._get_bilibili_transcript(
                    downloader=downloader,
                    video_url=video_url,
                    audio_meta=audio_meta,
                    quality=quality,
                    audio_cache_file=audio_cache_file,
                    transcript_cache_file=transcript_cache_file,
                    status_phase=TaskStatus.TRANSCRIBING,
                    output_path=output_path,
                    task_id=task_id,
                )
            else:
                # 1. 下载音频/视频
                audio_meta = self._download_media(
                    downloader=downloader,
                    video_url=video_url,
                    quality=quality,
                    audio_cache_file=audio_cache_file,
                    status_phase=TaskStatus.DOWNLOADING,
                    platform=platform,
                    output_path=output_path,
                    screenshot=screenshot,
                    video_understanding=video_understanding,
                    video_interval=video_interval,
                    grid_size=grid_size,
                )

                # 2. 获取字幕/转写文字
                # 优先尝试获取平台字幕，没有再 fallback 到音频转写
                transcript = self._get_transcript(
                    downloader=downloader,
                    video_url=video_url,
                    audio_file=audio_meta.file_path,
                    transcript_cache_file=transcript_cache_file,
                    status_phase=TaskStatus.TRANSCRIBING,
                    task_id=task_id,
                )

            # 3. GPT 总结
            markdown = self._summarize_text(
                audio_meta=audio_meta,
                transcript=transcript,
                gpt=gpt,
                markdown_cache_file=markdown_cache_file,
                link=link,
                screenshot=screenshot,
                formats=_format or [],
                style=style,
                extras=extras,
                video_img_urls=self.video_img_urls,
            )

            # 4. 截图 & 链接替换
            if _format:
                markdown = self._post_process_markdown(
                    markdown=markdown,
                    video_path=self.video_path,
                    formats=_format,
                    audio_meta=audio_meta,
                    platform=platform,
                )

            # 5. 保存记录到数据库
            self._update_status(task_id, TaskStatus.SAVING)
            self._save_metadata(video_id=audio_meta.video_id, platform=platform, task_id=task_id)

            # 6. 完成
            self._update_status(task_id, TaskStatus.SUCCESS)
            logger.info(f"笔记生成成功 (task_id={task_id})")
            return NoteResult(markdown=markdown, transcript=transcript, audio_meta=audio_meta)

        except Exception as exc:
            logger.error(f"生成笔记流程异常 (task_id={task_id})：{exc}", exc_info=True)
            self._update_status(task_id, TaskStatus.FAILED, message=str(exc))
            return None
        finally:
            self.progress_callback = None

    @staticmethod
    def delete_note(video_id: str, platform: str) -> int:
        """
        删除数据库中对应 video_id 与 platform 的任务记录

        :param video_id: 视频 ID
        :param platform: 平台标识
        :return: 删除的记录数
        """
        logger.info(f"删除笔记记录 (video_id={video_id}, platform={platform})")
        return delete_task_by_video(video_id, platform)

    # ---------------- 私有方法 ----------------

    def _init_transcriber(self) -> Transcriber:
        """
        根据环境变量 TRANSCRIBER_TYPE 动态获取并实例化转写器
        """
        if self.transcriber_type not in _transcribers:
            logger.error(f"未找到支持的转写器：{self.transcriber_type}")
            raise Exception(f"不支持的转写器：{self.transcriber_type}")

        logger.info(f"使用转写器：{self.transcriber_type}")
        return get_transcriber(transcriber_type=self.transcriber_type)

    def _get_gpt(self, model_name: Optional[str], provider_id: Optional[str]) -> GPT:
        """
        根据 provider_id 获取对应的 GPT 实例
        :param model_name: GPT 模型名称
        :param provider_id: 供应商 ID
        :return: GPT 实例
        """
        provider = ProviderService.get_provider_by_id(provider_id)
        if not provider:
            logger.error(f"[get_gpt] 未找到模型供应商: provider_id={provider_id}")
            raise ProviderError(code=ProviderErrorEnum.NOT_FOUND,message=ProviderErrorEnum.NOT_FOUND.message)
        logger.info(f"创建 GPT 实例 {provider_id}")
        config = ModelConfig(
            api_key=provider["api_key"],
            base_url=provider["base_url"],
            model_name=model_name,
            provider=provider["type"],
            name=provider["name"],
        )
        return GPTFactory().from_config(config)

    def _get_downloader(self, platform: str) -> Downloader:
        """
        根据平台名称获取对应的下载器实例

        :param platform: 平台标识，需在 SUPPORT_PLATFORM_MAP 中
        :return: 对应的 Downloader 子类实例
        """
        downloader_cls = SUPPORT_PLATFORM_MAP.get(platform)
        logger.debug(f"实例化下载器 -  {platform}")
        instance = None
        if not downloader_cls:
            logger.error(f"不支持的平台：{platform}")
            raise NoteError(code=NoteErrorEnum.PLATFORM_NOT_SUPPORTED.code,
                            message=NoteErrorEnum.PLATFORM_NOT_SUPPORTED.message)
        try:
            instance = downloader_cls
        except Exception as e:
            logger.error(f"实例化下载器失败：{e}")


        logger.info(f"使用下载器：{downloader_cls.__class__}")
        return instance

    def _update_status(self, task_id: Optional[str], status: Union[str, TaskStatus], message: Optional[str] = None):
        """
        创建或更新 {task_id}.status.json，记录当前任务状态

        :param task_id: 任务唯一 ID
        :param status: TaskStatus 枚举或自定义状态字符串
        :param message: 可选消息，用于记录失败原因等
        """
        status_value = status.value if isinstance(status, TaskStatus) else status
        if self.progress_callback is not None:
            try:
                self.progress_callback(str(status_value), message)
            except Exception as exc:
                logger.warning(f"外部进度回调失败：{exc}")

        if not task_id:
            return

        NOTE_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        status_file = NOTE_OUTPUT_DIR / f"{task_id}.status.json"
        status_message = f"写入状态文件: {status_file} 当前状态: {status}"
        if message:
            status_message += f" 消息: {message}"
        print(status_message)
        data = {"status": status_value}
        if message:
            data["message"] = message

        try:
            # First create a temporary file
            temp_file = status_file.with_suffix('.tmp')

            # Write to temporary file
            with temp_file.open('w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            # Atomic rename operation
            temp_file.replace(status_file)

            print(f"状态文件写入成功: {status_file}")
        except Exception as e:
            logger.error(f"写入状态文件失败 (task_id={task_id})：{e}")
            # Try to write error to file directly as fallback
            try:
                with status_file.open('w', encoding='utf-8') as f:
                    f.write(f"Error writing status: {str(e)}")
            except:
                logger.error(f"写入错误  {e}")

    def _handle_exception(self, task_id, exc):
        logger.error(f"任务异常 (task_id={task_id})", exc_info=True)
        error_message = getattr(exc, 'detail', str(exc))
        if isinstance(error_message, dict):
            try:
                error_message = json.dumps(error_message, ensure_ascii=False)
            except:
                error_message = str(error_message)
        self._update_status(task_id, TaskStatus.FAILED, message=error_message)

    def _run_with_status_heartbeat(
        self,
        *,
        task_id: Optional[str],
        status: TaskStatus,
        heartbeat_message: str,
        operation: Callable[[], Any],
    ) -> Any:
        if not task_id or OPERATION_HEARTBEAT_SECONDS <= 0:
            return operation()

        stop_event = Event()

        def heartbeat_loop() -> None:
            while not stop_event.wait(OPERATION_HEARTBEAT_SECONDS):
                self._update_status(task_id, status, message=heartbeat_message)

        heartbeat_thread = Thread(target=heartbeat_loop, daemon=True)
        heartbeat_thread.start()
        try:
            return operation()
        finally:
            stop_event.set()
            heartbeat_thread.join(timeout=OPERATION_HEARTBEAT_SECONDS)

    def _get_bilibili_metadata(
        self,
        downloader: BilibiliDownloader,
        video_url: Union[str, HttpUrl],
        audio_cache_file: Path,
        status_phase: TaskStatus,
        output_path: Optional[str],
    ) -> AudioDownloadResult:
        """
        仅获取 B 站视频元数据，为字幕优先路径准备标题、时长和标签等信息。
        """
        task_id = audio_cache_file.stem.split("_")[0]
        self._update_status(task_id, status_phase)

        if audio_cache_file.exists():
            logger.info(f"检测到媒体缓存 ({audio_cache_file})，尝试读取")
            try:
                data = json.loads(audio_cache_file.read_text(encoding="utf-8"))
                return AudioDownloadResult(**data)
            except Exception as e:
                logger.warning(f"读取媒体缓存失败，将重新获取元数据：{e}")

        logger.info("开始获取 B 站视频元数据")
        audio_meta = self._run_with_status_heartbeat(
            task_id=task_id,
            status=status_phase,
            heartbeat_message="视频元数据获取中",
            operation=lambda: downloader.fetch_metadata(video_url=video_url, output_dir=output_path),
        )
        audio_cache_file.write_text(
            json.dumps(asdict(audio_meta), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        logger.info(f"视频元数据缓存成功 ({audio_cache_file})")
        return audio_meta

    def _prepare_video_assets(
        self,
        downloader: Downloader,
        video_url: Union[str, HttpUrl],
        task_id: Optional[str],
        output_path: Optional[str],
        video_interval: int,
        grid_size: List[int],
    ) -> None:
        """
        仅在需要截图或视频理解时下载视频并生成相关素材。
        """
        self._update_status(task_id, TaskStatus.DOWNLOADING)

        try:
            logger.info("开始下载视频")
            video_path_str = self._run_with_status_heartbeat(
                task_id=task_id,
                status=TaskStatus.DOWNLOADING,
                heartbeat_message="视频下载进行中",
                operation=lambda: downloader.download_video(video_url, output_dir=output_path),
            )
            self.video_path = Path(video_path_str)
            logger.info(f"视频下载完成：{self.video_path}")

            if grid_size:
                self.video_img_urls = VideoReader(
                    video_path=str(self.video_path),
                    grid_size=tuple(grid_size),
                    frame_interval=video_interval,
                    unit_width=1280,
                    unit_height=720,
                    save_quality=90,
                ).run()
            else:
                logger.info("未指定 grid_size，跳过缩略图生成")
        except Exception as exc:
            logger.error(f"视频下载失败：{exc}")
            self._handle_exception(task_id, exc)
            raise

    def _get_bilibili_transcript(
        self,
        downloader: BilibiliDownloader,
        video_url: str,
        audio_meta: AudioDownloadResult,
        quality: DownloadQuality,
        audio_cache_file: Path,
        transcript_cache_file: Path,
        status_phase: TaskStatus,
        output_path: Optional[str],
        task_id: Optional[str],
    ) -> Tuple[TranscriptResult | None, AudioDownloadResult]:
        """
        B 站专用转写流程：平台字幕 -> 下载音频本地转写。
        """
        self._update_status(task_id, status_phase)

        if transcript_cache_file.exists():
            logger.info(f"检测到转写缓存 ({transcript_cache_file})，尝试读取")
            try:
                data = json.loads(transcript_cache_file.read_text(encoding="utf-8"))
                segments = [TranscriptSegment(**seg) for seg in data.get("segments", [])]
                transcript = TranscriptResult(
                    language=data.get("language"),
                    full_text=data["full_text"],
                    segments=segments,
                )
                return transcript, audio_meta
            except Exception as e:
                logger.warning(f"加载转写缓存失败，将重新获取：{e}")

        logger.info("尝试获取 B 站字幕（平台字幕 -> 本地转写）...")
        try:
            transcript = self._run_with_status_heartbeat(
                task_id=task_id,
                status=status_phase,
                heartbeat_message="平台字幕获取中",
                operation=lambda: downloader.download_subtitles(video_url),
            )
            if transcript and transcript.segments:
                logger.info(f"成功获取 B 站字幕，共 {len(transcript.segments)} 段")
                transcript_cache_file.write_text(
                    json.dumps(asdict(transcript), ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )
                return transcript, audio_meta
            logger.info("B 站字幕不可用，将下载音频并使用本地转写")
        except Exception as e:
            logger.warning(f"获取 B 站字幕失败: {e}，将下载音频并使用本地转写")

        audio_meta = self._ensure_audio_downloaded(
            downloader=downloader,
            video_url=video_url,
            quality=quality,
            audio_meta=audio_meta,
            audio_cache_file=audio_cache_file,
            output_path=output_path,
        )
        transcript = self._transcribe_audio(
            audio_file=audio_meta.file_path,
            transcript_cache_file=transcript_cache_file,
            status_phase=status_phase,
        )
        return transcript, audio_meta

    def _ensure_audio_downloaded(
        self,
        downloader: Downloader,
        video_url: Union[str, HttpUrl],
        quality: DownloadQuality,
        audio_meta: AudioDownloadResult,
        audio_cache_file: Path,
        output_path: Optional[str],
    ) -> AudioDownloadResult:
        """
        仅在需要本地转写时才下载音频，并覆盖缓存中的 file_path。
        """
        task_id = audio_cache_file.stem.split("_")[0]
        self._update_status(task_id, TaskStatus.DOWNLOADING)

        if audio_meta.file_path and Path(audio_meta.file_path).exists():
            logger.info(f"检测到已下载音频文件，直接复用: {audio_meta.file_path}")
            return audio_meta

        logger.info("开始下载音频（仅在字幕不可用时触发）")
        downloaded_audio = self._run_with_status_heartbeat(
            task_id=task_id,
            status=TaskStatus.DOWNLOADING,
            heartbeat_message="音频下载进行中",
            operation=lambda: downloader.download(
                video_url=video_url,
                quality=quality,
                output_dir=output_path,
                need_video=False,
            ),
        )
        audio_cache_file.write_text(
            json.dumps(asdict(downloaded_audio), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        logger.info(f"音频下载并缓存成功 ({audio_cache_file})")
        return downloaded_audio

    def _download_media(
        self,
        downloader: Downloader,
        video_url: Union[str, HttpUrl],
        quality: DownloadQuality,
        audio_cache_file: Path,
        status_phase: TaskStatus,
        platform: str,
        output_path: Optional[str],
        screenshot: bool,
        video_understanding: bool,
        video_interval: int,
        grid_size: List[int],
    ) -> AudioDownloadResult | None:
        """
        1. 检查音频缓存；若不存在，则根据需要下载音频或视频（若需截图/可视化）。
        2. 如果需要视频，则先下载视频并生成缩略图集，再下载音频。
        3. 返回 AudioDownloadResult

        :param downloader: Downloader 实例
        :param video_url: 视频/音频链接
        :param quality: 音频下载质量
        :param audio_cache_file: 本地缓存 JSON 文件路径
        :param status_phase: 对应的状态枚举，如 TaskStatus.DOWNLOADING
        :param platform: 平台标识
        :param output_path: 下载输出目录（可为 None）
        :param screenshot: 是否需要在笔记中插入截图
        :param video_understanding: 是否需要生成缩略图
        :param video_interval: 视频截帧间隔
        :param grid_size: 缩略图网格尺寸
        :return: AudioDownloadResult 对象
        """
        task_id = audio_cache_file.stem.split("_")[0]
        self._update_status(task_id, status_phase)



        # 判断是否需要下载视频
        need_video = screenshot or video_understanding
        if need_video:
            try:
                logger.info("开始下载视频")
                video_path_str = self._run_with_status_heartbeat(
                    task_id=task_id,
                    status=status_phase,
                    heartbeat_message="视频下载进行中",
                    operation=lambda: downloader.download_video(video_url),
                )
                self.video_path = Path(video_path_str)
                logger.info(f"视频下载完成：{self.video_path}")

                # 若指定了 grid_size，则生成缩略图
                if grid_size:
                    self.video_img_urls=VideoReader(
                        video_path=str(self.video_path),
                        grid_size=tuple(grid_size),
                        frame_interval=video_interval,
                        unit_width=1280,
                        unit_height=720,
                        save_quality=90,
                    ).run()
                else:
                    logger.info("未指定 grid_size，跳过缩略图生成")
            except Exception as exc:
                logger.error(f"视频下载失败：{exc}")

                self._handle_exception(task_id, exc)
                raise
        # 已有缓存，尝试加载
        if audio_cache_file.exists():
            logger.info(f"检测到音频缓存 ({audio_cache_file})，直接读取")
            try:
                data = json.loads(audio_cache_file.read_text(encoding="utf-8"))
                return AudioDownloadResult(**data)
            except Exception as e:
                logger.warning(f"读取音频缓存失败，将重新下载：{e}")
        # 下载音频
        try:
            logger.info("开始下载音频")
            audio = self._run_with_status_heartbeat(
                task_id=task_id,
                status=status_phase,
                heartbeat_message="音频下载进行中",
                operation=lambda: downloader.download(
                    video_url=video_url,
                    quality=quality,
                    output_dir=output_path,
                    need_video=need_video,
                ),
            )
            # 缓存 audio 元信息到本地 JSON
            audio_cache_file.write_text(json.dumps(asdict(audio), ensure_ascii=False, indent=2), encoding="utf-8")
            logger.info(f"音频下载并缓存成功 ({audio_cache_file})")
            return audio
        except Exception as exc:
            logger.error(f"音频下载失败：{exc}")
            self._handle_exception(task_id, exc)
            raise


    def _get_transcript(
        self,
        downloader: Downloader,
        video_url: str,
        audio_file: str,
        transcript_cache_file: Path,
        status_phase: TaskStatus,
        task_id: Optional[str] = None,
    ) -> TranscriptResult | None:
        """
        优先获取平台字幕，没有则 fallback 到音频转写

        :param downloader: 下载器实例
        :param video_url: 视频链接
        :param audio_file: 音频文件路径（用于 fallback 转写）
        :param transcript_cache_file: 缓存文件路径
        :param status_phase: 状态枚举
        :param task_id: 任务 ID
        :return: TranscriptResult 对象
        """
        self._update_status(task_id, status_phase)

        # 已有缓存，直接返回
        if transcript_cache_file.exists():
            logger.info(f"检测到转写缓存 ({transcript_cache_file})，尝试读取")
            try:
                data = json.loads(transcript_cache_file.read_text(encoding="utf-8"))
                segments = [TranscriptSegment(**seg) for seg in data.get("segments", [])]
                return TranscriptResult(language=data.get("language"), full_text=data["full_text"], segments=segments)
            except Exception as e:
                logger.warning(f"加载转写缓存失败，将重新获取：{e}")

        # 1. 先尝试获取平台字幕
        logger.info("尝试获取平台字幕...")
        try:
            transcript = self._run_with_status_heartbeat(
                task_id=task_id,
                status=status_phase,
                heartbeat_message="平台字幕获取中",
                operation=lambda: downloader.download_subtitles(video_url),
            )
            if transcript and transcript.segments:
                logger.info(f"成功获取平台字幕，共 {len(transcript.segments)} 段")
                # 缓存结果
                transcript_cache_file.write_text(
                    json.dumps(asdict(transcript), ensure_ascii=False, indent=2),
                    encoding="utf-8"
                )
                return transcript
            else:
                logger.info("平台无可用字幕，将使用音频转写")
        except Exception as e:
            logger.warning(f"获取平台字幕失败: {e}，将使用音频转写")

        # 2. Fallback 到音频转写
        return self._transcribe_audio(
            audio_file=audio_file,
            transcript_cache_file=transcript_cache_file,
            status_phase=status_phase,
        )

    def _transcribe_audio(
        self,
        audio_file: str,
        transcript_cache_file: Path,
        status_phase: TaskStatus,
    ) -> TranscriptResult | None:
        """
        1. 检查转写缓存；若存在则尝试加载，否则调用转写器生成并缓存。
        2. 返回 TranscriptResult 对象

        :param audio_file: 音频文件本地路径
        :param transcript_cache_file: 转写结果缓存路径
        :param status_phase: 对应的状态枚举，如 TaskStatus.TRANSCRIBING
        :return: TranscriptResult 对象
        """
        task_id = transcript_cache_file.stem.split("_")[0]
        self._update_status(task_id, status_phase)

        # 已有缓存，尝试加载
        if transcript_cache_file.exists():
            logger.info(f"检测到转写缓存 ({transcript_cache_file})，尝试读取")
            try:
                data = json.loads(transcript_cache_file.read_text(encoding="utf-8"))
                segments = [TranscriptSegment(**seg) for seg in data.get("segments", [])]
                return TranscriptResult(language=data["language"], full_text=data["full_text"], segments=segments)
            except Exception as e:
                logger.warning(f"加载转写缓存失败，将重新转写：{e}")

        # 调用转写器
        try:
            logger.info("开始转写音频")
            transcript = self._run_with_status_heartbeat(
                task_id=task_id,
                status=status_phase,
                heartbeat_message="本地转写进行中",
                operation=lambda: self.transcriber.transcript(file_path=audio_file),
            )
            transcript_cache_file.write_text(json.dumps(asdict(transcript), ensure_ascii=False, indent=2), encoding="utf-8")
            logger.info(f"转写并缓存成功 ({transcript_cache_file})")
            return transcript
        except Exception as exc:
            logger.error(f"音频转写失败：{exc}")
            self._handle_exception(task_id, exc)
            raise

    def _summarize_text(
        self,
        audio_meta: AudioDownloadResult,
        transcript: TranscriptResult,
        gpt: GPT,
        markdown_cache_file: Path,
        link: bool,
        screenshot: bool,
        formats: List[str],
        style: Optional[str],
        extras: Optional[str],
            video_img_urls: List[str],
    ) -> str | None:
        """
        调用 GPT 对转写结果进行总结，生成 Markdown 文本并缓存。

        :param audio_meta: AudioDownloadResult 元信息
        :param transcript: TranscriptResult 转写结果
        :param gpt: GPT 实例
        :param markdown_cache_file: Markdown 缓存路径
        :param link: 是否在笔记中插入链接
        :param screenshot: 是否在笔记中生成截图占位
        :param formats: 包含 'link' 或 'screenshot' 的列表
        :param style: GPT 输出风格
        :param extras: GPT 额外参数
        :return: 生成的 Markdown 字符串
        """
        task_id = markdown_cache_file.stem
        self._update_status(task_id, TaskStatus.SUMMARIZING)

        source = GPTSource(
            title=audio_meta.title,
            segment=transcript.segments,
            tags=audio_meta.raw_info.get("tags", []),
            screenshot=screenshot,
            video_img_urls=video_img_urls,
            link=link,
            _format=formats,
            style=style,
            extras=extras,
        )

        try:
            def on_progress(message: str) -> None:
                self._update_status(task_id, TaskStatus.SUMMARIZING, message=message)

            markdown = gpt.summarize(source, progress_callback=on_progress)
            markdown = normalize_math_delimiters(markdown)
            markdown_cache_file.write_text(markdown, encoding="utf-8")
            logger.info(f"GPT 总结并缓存成功 ({markdown_cache_file})")
            return markdown
        except Exception as exc:
            logger.error(f"GPT 总结失败：{exc}")
            self._handle_exception(task_id, exc)
            raise

    def _post_process_markdown(
        self,
        markdown: str,
        video_path: Optional[Path],
        formats: List[str],
        audio_meta: AudioDownloadResult,
        platform: str,
    ) -> str:
        """
        对生成的 Markdown 做后期处理：插入截图和/或插入链接。

        :param markdown: 原始 Markdown 字符串
        :param video_path: 本地视频路径（可为 None）
        :param formats: 包含 'link' 或 'screenshot' 的列表
        :param audio_meta: AudioDownloadResult 元信息，用于链接替换
        :param platform: 平台标识，用于链接替换
        :return: 处理后的 Markdown 字符串
        """
        if "screenshot" in formats and video_path:
            try:
                markdown = self._insert_screenshots(markdown, video_path)
            except Exception as exc:
                logger.warning("截图插入失败，跳过该步骤")

        if "link" in formats:
            try:
                markdown = replace_content_markers(markdown, video_id=audio_meta.video_id, platform=platform)
            except Exception as e:
                logger.warning(f"链接插入失败，跳过该步骤：{e}")

        return markdown

    def _insert_screenshots(self, markdown: str, video_path: Path) -> str | None | Any:
        """
        扫描 Markdown 文本中所有 Screenshot 标记，并替换为实际生成的截图链接。

        :param markdown: 含有 *Screenshot-mm:ss 或 Screenshot-[mm:ss] 标记的 Markdown 文本
        :param video_path: 本地视频文件路径
        :return: 替换后的 Markdown 字符串
        """
        matches: List[Tuple[str, int]] = self._extract_screenshot_timestamps(markdown)
        for idx, (marker, ts) in enumerate(matches):
            try:
                img_path = generate_screenshot(str(video_path), str(IMAGE_OUTPUT_DIR), ts, idx)
                filename = Path(img_path).name
                # 构建前端可访问的 URL，例如 /static/screenshots/{filename}
                img_url = f"{IMAGE_BASE_URL.rstrip('/')}/{filename}"
                markdown = markdown.replace(marker, f"![]({img_url})", 1)
            except Exception as exc:
                logger.error(f"生成截图失败 (timestamp={ts})：{exc}")
                # self._handle_exception(task_id, exc)
                return None
        return markdown

    @staticmethod
    def _extract_screenshot_timestamps(markdown: str) -> List[Tuple[str, int]]:
        """
        从 Markdown 文本中提取所有 '*Screenshot-mm:ss' 或 'Screenshot-[mm:ss]' 标记，
        返回 [(原始标记文本, 时间戳秒数), ...] 列表。

        :param markdown: 原始 Markdown 文本
        :return: 标记与对应时间戳秒数的列表
        """
        pattern = r"(?:\*Screenshot-(\d{2}):(\d{2})|Screenshot-\[(\d{2}):(\d{2})\])"
        results: List[Tuple[str, int]] = []
        for match in re.finditer(pattern, markdown):
            mm = match.group(1) or match.group(3)
            ss = match.group(2) or match.group(4)
            total_seconds = int(mm) * 60 + int(ss)
            results.append((match.group(0), total_seconds))
        return results

    def _save_metadata(self, video_id: str, platform: str, task_id: str) -> None:
        """
        将生成的笔记任务记录插入数据库

        :param video_id: 视频 ID
        :param platform: 平台标识
        :param task_id: 任务 ID
        """
        try:
            insert_video_task(video_id=video_id, platform=platform, task_id=task_id)
            logger.info(f"已保存任务记录到数据库 (video_id={video_id}, platform={platform}, task_id={task_id})")
        except Exception as e:
            logger.error(f"保存任务记录失败：{e}")
