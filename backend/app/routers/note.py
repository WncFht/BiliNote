# app/routers/note.py
import ipaddress
import json
import math
import os
import re
import socket
import uuid
from dataclasses import asdict
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

import httpx
from fastapi import APIRouter, BackgroundTasks, File, HTTPException, Request, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, field_validator

from app.db.video_task_dao import delete_task_by_id, delete_task_by_video, list_video_tasks
from app.enmus.exception import NoteErrorEnum
from app.enmus.note_enums import DownloadQuality
from app.enmus.task_status_enums import TaskStatus
from app.exceptions.note import NoteError
from app.services.note import NoteGenerator, logger
from app.utils.response import ResponseWrapper as R
from app.utils.url_parser import extract_video_id
from app.validators.video_url_validator import is_supported_video_url

# from app.services.downloader import download_raw_audio
# from app.services.whisperer import transcribe_audio

router = APIRouter()
UPLOAD_FILENAME_RE = re.compile(r"[^A-Za-z0-9._-]+")
BLOCKED_PROXY_HOSTS = {"localhost", "127.0.0.1", "::1", "0.0.0.0", "host.docker.internal"}


class RecordRequest(BaseModel):
    video_id: Optional[str] = None
    platform: Optional[str] = None
    task_id: Optional[str] = None


class VideoRequest(BaseModel):
    video_url: str
    platform: str
    quality: DownloadQuality
    screenshot: Optional[bool] = False
    link: Optional[bool] = False
    model_name: str
    provider_id: str
    task_id: Optional[str] = None
    format: Optional[list] = []
    style: str = None
    extras: Optional[str]=None
    video_understanding: Optional[bool] = False
    video_interval: Optional[int] = 0
    grid_size: Optional[list] = []

    @field_validator("video_url")
    def validate_supported_url(cls, v):
        url = str(v)
        parsed = urlparse(url)
        if parsed.scheme in ("http", "https"):
            # 是网络链接，继续用原有平台校验
            if not is_supported_video_url(url):
                raise NoteError(code=NoteErrorEnum.PLATFORM_NOT_SUPPORTED.code,
                                message=NoteErrorEnum.PLATFORM_NOT_SUPPORTED.message)

        return v


def normalize_web_generation_options(
    *,
    screenshot: bool = False,
    _format: Optional[list] = None,
    video_understanding: bool = False,
    video_interval: Optional[int] = 0,
    grid_size: Optional[list] = None,
) -> dict:
    del screenshot, video_understanding, grid_size

    normalized_formats = []
    for item in _format or []:
        if item == "screenshot":
            continue
        if item in normalized_formats:
            continue
        normalized_formats.append(item)

    return {
        "screenshot": False,
        "_format": normalized_formats,
        "video_understanding": False,
        "video_interval": video_interval if video_interval is not None else 0,
        "grid_size": [],
    }


NOTE_OUTPUT_DIR = os.getenv("NOTE_OUTPUT_DIR", "note_results")
UPLOAD_DIR = "uploads"


def _is_blocked_proxy_ip(address: str) -> bool:
    parsed = ipaddress.ip_address(address)
    return any((
        parsed.is_private,
        parsed.is_loopback,
        parsed.is_link_local,
        parsed.is_multicast,
        parsed.is_reserved,
        parsed.is_unspecified,
    ))


def build_safe_upload_name(filename: str) -> str:
    candidate = (filename or "upload.bin").replace("\\", "/").split("/")[-1]
    if not candidate or candidate in {".", ".."}:
        candidate = "upload.bin"

    source_path = Path(candidate)
    safe_stem = UPLOAD_FILENAME_RE.sub("_", source_path.stem)
    if not re.search(r"[A-Za-z0-9]", safe_stem):
        safe_stem = "upload"

    safe_suffix = UPLOAD_FILENAME_RE.sub("", source_path.suffix)
    return f"{uuid.uuid4().hex}-{safe_stem}{safe_suffix}"


def validate_image_proxy_url(raw_url: str) -> str:
    parsed = urlparse(raw_url)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError("仅支持代理 http/https 图片地址")

    if not parsed.hostname:
        raise ValueError("图片地址缺少主机名")

    if parsed.username or parsed.password:
        raise ValueError("图片地址不支持携带认证信息")

    host = parsed.hostname.lower()
    if host in BLOCKED_PROXY_HOSTS or host.endswith(".local"):
        raise ValueError("不允许代理本地或内网地址")

    try:
        if re.fullmatch(r"\[[0-9A-Fa-f:]+\]", host):
            normalized_host = host[1:-1]
        else:
            normalized_host = host

        try:
            if _is_blocked_proxy_ip(normalized_host):
                raise ValueError("不允许代理本地或内网地址")
        except ValueError as exc:
            if str(exc) == "不允许代理本地或内网地址":
                raise
        except Exception:
            pass

        resolved = socket.getaddrinfo(host, parsed.port or (443 if parsed.scheme == "https" else 80))
        for result in resolved:
            address = result[4][0]
            if _is_blocked_proxy_ip(address):
                raise ValueError("不允许代理本地或内网地址")
    except socket.gaierror as exc:
        raise ValueError("图片地址无法解析") from exc

    return raw_url


def save_note_to_file(task_id: str, note):
    os.makedirs(NOTE_OUTPUT_DIR, exist_ok=True)
    with open(os.path.join(NOTE_OUTPUT_DIR, f"{task_id}.json"), "w", encoding="utf-8") as f:
        json.dump(asdict(note), f, ensure_ascii=False, indent=2)


def _load_json_file(path: str):
    if not os.path.exists(path):
        return None

    try:
        with open(path, "r", encoding="utf-8") as file:
            return json.load(file)
    except (OSError, json.JSONDecodeError):
        return None


def _load_text_file(path: str):
    if not os.path.exists(path):
        return None

    try:
        with open(path, "r", encoding="utf-8") as file:
            content = file.read().strip()
    except OSError:
        return None

    return content or None


def _load_legacy_task_result(task_id: str):
    audio_meta = _load_json_file(os.path.join(NOTE_OUTPUT_DIR, f"{task_id}_audio.json"))
    transcript = _load_json_file(os.path.join(NOTE_OUTPUT_DIR, f"{task_id}_transcript.json"))
    markdown = _load_text_file(os.path.join(NOTE_OUTPUT_DIR, f"{task_id}_markdown.md"))

    if not any((audio_meta, transcript, markdown)):
        return None

    return {
        "markdown": markdown or "",
        "transcript": transcript or {},
        "audio_meta": audio_meta or {},
    }


def _json_safe_value(value):
    if isinstance(value, dict):
        return {key: _json_safe_value(item) for key, item in value.items()}

    if isinstance(value, list):
        return [_json_safe_value(item) for item in value]

    if isinstance(value, float):
        return value if math.isfinite(value) else None

    return value


def load_task_snapshot(task_id: str):
    status_path = os.path.join(NOTE_OUTPUT_DIR, f"{task_id}.status.json")
    result_path = os.path.join(NOTE_OUTPUT_DIR, f"{task_id}.json")

    status_content = _load_json_file(status_path) or {}
    result_content = _load_json_file(result_path) or _load_legacy_task_result(task_id)
    result_content = _json_safe_value(result_content)

    status = status_content.get("status")
    message = status_content.get("message", "")

    if result_content and not status:
        status = TaskStatus.SUCCESS.value

    if not status:
        status = TaskStatus.PENDING.value

    return {
        "status": status,
        "message": message,
        "result": result_content,
    }


def delete_task_artifacts(task_id: str) -> int:
    removed = 0
    artifact_names = [
        f"{task_id}.json",
        f"{task_id}.status.json",
        f"{task_id}_audio.json",
        f"{task_id}_transcript.json",
        f"{task_id}_markdown.md",
    ]

    for artifact_name in artifact_names:
        artifact_path = Path(NOTE_OUTPUT_DIR) / artifact_name
        if artifact_path.exists():
            artifact_path.unlink()
            removed += 1

    return removed


def serialize_task_history_entry(task_row) -> dict:
    snapshot = load_task_snapshot(task_row.task_id)
    created_at = task_row.created_at.isoformat() if getattr(task_row, "created_at", None) else ""

    return {
        "task_id": task_row.task_id,
        "platform": task_row.platform,
        "created_at": created_at,
        "status": snapshot["status"],
        "message": snapshot["message"],
        "result": snapshot["result"],
    }


def run_note_task(task_id: str, video_url: str, platform: str, quality: DownloadQuality,
                  link: bool = False, screenshot: bool = False, model_name: str = None, provider_id: str = None,
                  _format: list = None, style: str = None, extras: str = None, video_understanding: bool = False,
                  video_interval=0, grid_size=[]
                  ):

    if not model_name or not provider_id:
        raise HTTPException(status_code=400, detail="请选择模型和提供者")

    normalized_options = normalize_web_generation_options(
        screenshot=screenshot,
        _format=_format,
        video_understanding=video_understanding,
        video_interval=video_interval,
        grid_size=grid_size,
    )

    note = NoteGenerator().generate(
        video_url=video_url,
        platform=platform,
        quality=quality,
        task_id=task_id,
        model_name=model_name,
        provider_id=provider_id,
        link=link,
        _format=normalized_options["_format"],
        style=style,
        extras=extras,
        screenshot=normalized_options["screenshot"],
        video_understanding=normalized_options["video_understanding"],
        video_interval=normalized_options["video_interval"],
        grid_size=normalized_options["grid_size"],
    )
    logger.info(f"Note generated: {task_id}")
    if not note or not note.markdown:
        logger.warning(f"任务 {task_id} 执行失败，跳过保存")
        return
    save_note_to_file(task_id, note)



@router.post('/delete_task')
def delete_task(data: RecordRequest):
    try:
        if data.task_id:
            delete_task_by_id(data.task_id)
            delete_task_artifacts(data.task_id)
            return R.success(msg='删除成功')

        if data.video_id and data.platform:
            delete_task_by_video(data.video_id, data.platform)
            return R.success(msg='删除成功')

        return R.error(msg='缺少 task_id 或 video_id/platform', code=400, status_code=400)
    except Exception as e:
        return R.error(msg=e, status_code=500)


@router.post("/upload")
async def upload(file: UploadFile = File(...)):
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    safe_name = build_safe_upload_name(file.filename or "upload.bin")
    file_location = os.path.join(UPLOAD_DIR, safe_name)

    with open(file_location, "wb+") as f:
        f.write(await file.read())

    # 假设你静态目录挂载了 /uploads
    return R.success({"url": f"/uploads/{safe_name}"})


@router.post("/generate_note")
def generate_note(data: VideoRequest, background_tasks: BackgroundTasks):
    try:

        video_id = extract_video_id(data.video_url, data.platform)
        # if not video_id:
        #     raise HTTPException(status_code=400, detail="无法提取视频 ID")
        # existing = get_task_by_video(video_id, data.platform)
        # if existing:
        #     return R.error(
        #         msg='笔记已生成，请勿重复发起',
        #
        #     )
        if data.task_id:
            # 如果传了task_id，说明是重试！
            task_id = data.task_id
            # 更新之前的状态
            NoteGenerator()._update_status(task_id, TaskStatus.PENDING)
            logger.info(f"重试模式，复用已有 task_id={task_id}")
        else:
            # 正常新建任务
            task_id = str(uuid.uuid4())

        background_tasks.add_task(run_note_task, task_id, data.video_url, data.platform, data.quality, data.link,
                                  data.screenshot, data.model_name, data.provider_id, data.format, data.style,
                                  data.extras, data.video_understanding, data.video_interval, data.grid_size)
        return R.success({"task_id": task_id})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/task_status/{task_id}")
def get_task_status(task_id: str):
    snapshot = load_task_snapshot(task_id)
    status = snapshot["status"]
    message = snapshot["message"]
    result_content = snapshot["result"]

    if status == TaskStatus.SUCCESS.value:
        if result_content:
            return R.success({
                "status": status,
                "result": result_content,
                "message": message,
                "task_id": task_id
            })
        return R.success({
            "status": TaskStatus.PENDING.value,
            "message": "任务完成，但结果文件未找到",
            "task_id": task_id
        })

    if status == TaskStatus.FAILED.value:
        return R.error(message or "任务失败", code=500, status_code=500)

    if snapshot["result"]:
        return R.success({
            "status": status,
            "result": snapshot["result"],
            "message": message,
            "task_id": task_id
        })

    return R.success({
        "status": status,
        "message": message or "任务排队中",
        "task_id": task_id
    })


@router.get("/task_history")
def get_task_history(limit: int = 50):
    safe_limit = max(1, min(limit, 200))
    tasks = list_video_tasks(limit=safe_limit)
    payload = [serialize_task_history_entry(task_row) for task_row in tasks]
    return R.success(payload)


@router.get("/image_proxy")
async def image_proxy(request: Request, url: str):
    headers = {
        "Referer": "https://www.bilibili.com/",
        "User-Agent": request.headers.get("User-Agent", ""),
    }

    try:
        validated_url = validate_image_proxy_url(url)
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=False) as client:
            resp = await client.get(validated_url, headers=headers)

            if resp.status_code != 200:
                raise HTTPException(status_code=resp.status_code, detail="图片获取失败")

            content_type = resp.headers.get("Content-Type", "image/jpeg")
            return StreamingResponse(
                resp.aiter_bytes(),
                media_type=content_type,
                headers={
                    "Cache-Control": "public, max-age=86400",  #  缓存一天
                    "Content-Type": content_type,
                }
            )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
