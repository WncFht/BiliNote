import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from app.downloaders.bilibili_downloader import BilibiliDownloader
from app.models.audio_model import AudioDownloadResult
from app.models.transcriber_model import TranscriptResult, TranscriptSegment
from app.enmus.task_status_enums import TaskStatus
from app.services.note import NoteGenerator


class BilibiliDownloaderSubtitleFallbackTest(unittest.TestCase):
    def test_download_subtitles_returns_none_when_platform_subtitles_missing(self) -> None:
        downloader = BilibiliDownloader()

        with (
            patch("app.downloaders.bilibili_downloader.yt_dlp.YoutubeDL") as youtube_dl,
            patch("subprocess.run") as subprocess_run,
        ):
            youtube_dl.return_value.__enter__.return_value.extract_info.return_value = {
                "requested_subtitles": {}
            }

            transcript = downloader.download_subtitles(
                "https://www.bilibili.com/video/BV11UwDzzEMN/"
            )

        self.assertIsNone(transcript)
        subprocess_run.assert_not_called()

    def test_download_passes_cookiefile_to_ytdlp_when_available(self) -> None:
        downloader = BilibiliDownloader()

        with (
            patch.object(downloader, "_resolve_cookiefile", return_value="/tmp/cookies.txt"),
            patch("app.downloaders.bilibili_downloader.yt_dlp.YoutubeDL") as youtube_dl,
        ):
            youtube_dl.return_value.__enter__.return_value.extract_info.return_value = {
                "id": "BV11UwDzzEMN",
                "title": "测试标题",
                "duration": 12.0,
                "thumbnail": "https://example.com/cover.jpg",
            }

            downloader.download("https://www.bilibili.com/video/BV11UwDzzEMN/")

        ydl_opts = youtube_dl.call_args.args[0]
        self.assertEqual(ydl_opts.get("cookiefile"), "/tmp/cookies.txt")


class NoteGeneratorBilibiliFlowTest(unittest.TestCase):
    def setUp(self) -> None:
        init_patcher = patch.object(NoteGenerator, "_init_transcriber", return_value=Mock())
        self.addCleanup(init_patcher.stop)
        init_patcher.start()
        self.generator = NoteGenerator()

    def test_generate_uses_bilibili_subtitles_without_downloading_audio_first(self) -> None:
        fake_downloader = Mock()
        fake_downloader.fetch_metadata.return_value = AudioDownloadResult(
            file_path="",
            title="测试标题",
            duration=12.0,
            cover_url=None,
            platform="bilibili",
            video_id="BV11UwDzzEMN",
            raw_info={"tags": ["测试"]},
        )
        fake_downloader.download_subtitles.return_value = TranscriptResult(
            language="zh",
            full_text="测试字幕",
            segments=[TranscriptSegment(start=0.0, end=1.0, text="测试字幕")],
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            note_output_dir = Path(temp_dir)
            with (
                patch("app.services.note.NOTE_OUTPUT_DIR", note_output_dir),
                patch.object(self.generator, "_get_downloader", return_value=fake_downloader),
                patch.object(self.generator, "_get_gpt", return_value=Mock()),
                patch.object(
                    self.generator,
                    "_download_media",
                    side_effect=AssertionError("should not download audio when subtitles are available"),
                ),
                patch.object(self.generator, "_summarize_text", return_value="# 测试笔记\n"),
                patch.object(self.generator, "_save_metadata"),
                patch.object(self.generator, "_update_status"),
            ):
                result = self.generator.generate(
                    video_url="https://www.bilibili.com/video/BV11UwDzzEMN/",
                    platform="bilibili",
                    task_id="task-1",
                    model_name="gpt-5.4",
                    provider_id="openai",
                    link=False,
                    screenshot=False,
                    _format=[],
                    style="detailed",
                    extras=None,
                    output_path=temp_dir,
                    video_understanding=False,
                    video_interval=4,
                    grid_size=[],
                )

        self.assertIsNotNone(result)
        self.assertEqual(result.audio_meta.video_id, "BV11UwDzzEMN")
        fake_downloader.fetch_metadata.assert_called_once()
        fake_downloader.download_subtitles.assert_called_once()
        fake_downloader.download.assert_not_called()

    def test_ensure_audio_downloaded_emits_periodic_heartbeat_during_long_download(self) -> None:
        fake_downloader = Mock()
        fake_downloader.download.side_effect = lambda **kwargs: (
            time.sleep(0.05),
            AudioDownloadResult(
                file_path="downloaded.mp3",
                title="测试标题",
                duration=12.0,
                cover_url=None,
                platform="bilibili",
                video_id="BV11UwDzzEMN",
                raw_info={},
            ),
        )[1]

        initial_meta = AudioDownloadResult(
            file_path="",
            title="测试标题",
            duration=12.0,
            cover_url=None,
            platform="bilibili",
            video_id="BV11UwDzzEMN",
            raw_info={},
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            audio_cache_file = Path(temp_dir) / "task-1_audio.json"
            with (
                patch("app.services.note.OPERATION_HEARTBEAT_SECONDS", 0.01),
                patch.object(self.generator, "_update_status") as update_status,
            ):
                result = self.generator._ensure_audio_downloaded(
                    downloader=fake_downloader,
                    video_url="https://www.bilibili.com/video/BV11UwDzzEMN/",
                    quality="medium",
                    audio_meta=initial_meta,
                    audio_cache_file=audio_cache_file,
                    output_path=temp_dir,
                )

        self.assertEqual(result.file_path, "downloaded.mp3")
        transcribing_calls = [
            call
            for call in update_status.call_args_list
            if call.args[:2] == ("task-1", TaskStatus.DOWNLOADING)
        ]
        self.assertGreaterEqual(len(transcribing_calls), 2)
        self.assertIn(
            "音频下载进行中",
            [call.kwargs.get("message") for call in transcribing_calls],
        )

    def test_transcribe_audio_emits_periodic_heartbeat_during_long_transcription(self) -> None:
        self.generator.transcriber = Mock()
        self.generator.transcriber.transcript.side_effect = lambda file_path: (
            time.sleep(0.05),
            TranscriptResult(
                language="zh",
                full_text="测试字幕",
                segments=[TranscriptSegment(start=0.0, end=1.0, text="测试字幕")],
            ),
        )[1]

        with tempfile.TemporaryDirectory() as temp_dir:
            transcript_cache_file = Path(temp_dir) / "task-1_transcript.json"
            with (
                patch("app.services.note.OPERATION_HEARTBEAT_SECONDS", 0.01),
                patch.object(self.generator, "_update_status") as update_status,
            ):
                result = self.generator._transcribe_audio(
                    audio_file="downloaded.mp3",
                    transcript_cache_file=transcript_cache_file,
                    status_phase=TaskStatus.TRANSCRIBING,
                )

        self.assertEqual(result.full_text, "测试字幕")
        transcribing_calls = [
            call
            for call in update_status.call_args_list
            if call.args[:2] == ("task-1", TaskStatus.TRANSCRIBING)
        ]
        self.assertGreaterEqual(len(transcribing_calls), 2)
        self.assertIn(
            "本地转写进行中",
            [call.kwargs.get("message") for call in transcribing_calls],
        )


if __name__ == "__main__":
    unittest.main()
