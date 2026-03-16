import os
import tempfile
import unittest
from unittest.mock import patch

from app.transcriber.mlx_whisper_transcriber import MLXWhisperTranscriber


class MLXWhisperTranscriberRepoTest(unittest.TestCase):
    def test_base_model_uses_mlx_repo_name(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            with (
                patch.dict(os.environ, {"TRANSCRIBER_TYPE": "mlx-whisper"}, clear=False),
                patch("app.transcriber.mlx_whisper_transcriber.platform.system", return_value="Darwin"),
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


if __name__ == "__main__":
    unittest.main()
