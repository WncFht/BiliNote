from concurrent.futures import ThreadPoolExecutor
import os
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

from app.transcriber.mlx_whisper_transcriber import MLXWhisperTranscriber


class MLXWhisperTranscriberRepoTest(unittest.TestCase):
    def test_base_model_uses_mlx_repo_name(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            with (
                patch.dict(os.environ, {"TRANSCRIBER_TYPE": "mlx-whisper"}, clear=False),
                patch("app.transcriber.mlx_whisper_transcriber.platform.system", return_value="Darwin"),
                patch("app.transcriber.mlx_whisper_transcriber.MLX_WHISPER_INSTALLED", True),
                patch("app.transcriber.mlx_whisper_transcriber.get_model_dir", return_value=temp_dir),
                patch("app.transcriber.mlx_whisper_transcriber.Path.exists", return_value=False),
                patch("app.transcriber.mlx_whisper_transcriber.snapshot_download") as snapshot_download,
            ):
                MLXWhisperTranscriber(model_size="base")

        snapshot_download.assert_called_once()
        self.assertEqual(
            snapshot_download.call_args.args[0],
            "mlx-community/whisper-base-mlx",
        )

    def test_concurrent_transcripts_are_serialized_within_same_process(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            active_calls = 0
            max_active_calls = 0
            state_lock = threading.Lock()
            start_barrier = threading.Barrier(3)

            def fake_transcribe(*args, **kwargs):
                nonlocal active_calls, max_active_calls
                del args, kwargs
                with state_lock:
                    active_calls += 1
                    max_active_calls = max(max_active_calls, active_calls)
                time.sleep(0.05)
                with state_lock:
                    active_calls -= 1
                return {
                    "language": "zh",
                    "segments": [
                        {
                            "start": 0.0,
                            "end": 1.0,
                            "text": "测试字幕",
                        }
                    ],
                }

            def run_transcript(transcriber: MLXWhisperTranscriber, path: str):
                start_barrier.wait()
                return transcriber.transcript(path)

            with (
                patch.dict(os.environ, {"TRANSCRIBER_TYPE": "mlx-whisper"}, clear=False),
                patch("app.transcriber.mlx_whisper_transcriber.platform.system", return_value="Darwin"),
                patch("app.transcriber.mlx_whisper_transcriber.MLX_WHISPER_INSTALLED", True),
                patch("app.transcriber.mlx_whisper_transcriber.get_model_dir", return_value=temp_dir),
                patch("app.transcriber.mlx_whisper_transcriber.Path.exists", return_value=True),
                patch("app.transcriber.mlx_whisper_transcriber.mlx_whisper.transcribe", side_effect=fake_transcribe),
            ):
                first = MLXWhisperTranscriber(model_size="base")
                second = MLXWhisperTranscriber(model_size="base")

                with ThreadPoolExecutor(max_workers=2) as executor:
                    future_1 = executor.submit(run_transcript, first, "first.mp3")
                    future_2 = executor.submit(run_transcript, second, "second.mp3")
                    start_barrier.wait()
                    result_1 = future_1.result()
                    result_2 = future_2.result()

        self.assertEqual(result_1.full_text, "测试字幕")
        self.assertEqual(result_2.full_text, "测试字幕")
        self.assertEqual(max_active_calls, 1)


if __name__ == "__main__":
    unittest.main()
