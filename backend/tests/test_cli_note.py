import tempfile
import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch

from typer.testing import CliRunner

from app.models.audio_model import AudioDownloadResult
from app.models.notes_model import NoteResult
from app.models.transcriber_model import TranscriptResult
from app.cli.note import app


class BiliNoteCliContractTest(unittest.TestCase):
    def setUp(self) -> None:
        self.runner = CliRunner()
        self.fake_result = NoteResult(
            markdown="# test note\n",
            transcript=TranscriptResult(language="zh", full_text="hello", segments=[]),
            audio_meta=AudioDownloadResult(
                file_path="test.mp3",
                title="test title",
                duration=1.0,
                cover_url=None,
                platform="bilibili",
                video_id="BV1test",
                raw_info={},
            ),
        )

    def test_help_mentions_style_and_no_screenshot_flags(self) -> None:
        repo_root = Path(__file__).resolve().parents[2]
        result = subprocess.run(
            ["uv", "run", "bilinote-cli", "--help"],
            cwd=repo_root / "backend",
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0)
        self.assertIn("--style", result.stdout)
        self.assertIn("--no-screenshot", result.stdout)

    def test_cli_uses_expected_defaults_for_generation(self) -> None:
        with (
            patch("app.cli.note.initialize_runtime"),
            patch("app.cli.note.note_generator_class") as note_generator_cls,
        ):
            note_generator_cls.return_value.return_value.generate.return_value = self.fake_result

            result = self.runner.invoke(app, ["https://www.bilibili.com/video/BV19CwVz7EAU"])

        self.assertEqual(result.exit_code, 0)
        note_generator_cls.return_value.return_value.generate.assert_called_once()
        kwargs = note_generator_cls.return_value.return_value.generate.call_args.kwargs
        self.assertEqual(kwargs["platform"], "bilibili")
        self.assertEqual(kwargs["provider_id"], "openai")
        self.assertEqual(kwargs["model_name"], "gpt-5.4")
        self.assertEqual(kwargs["style"], "detailed")
        self.assertTrue(kwargs["screenshot"])
        self.assertTrue(kwargs["video_understanding"])
        self.assertEqual(kwargs["video_interval"], 4)
        self.assertEqual(kwargs["grid_size"], [3, 3])
        self.assertEqual(kwargs["_format"], ["toc", "summary", "screenshot"])

    def test_cli_respects_style_and_no_screenshot(self) -> None:
        with (
            patch("app.cli.note.initialize_runtime"),
            patch("app.cli.note.note_generator_class") as note_generator_cls,
        ):
            note_generator_cls.return_value.return_value.generate.return_value = self.fake_result

            result = self.runner.invoke(
                app,
                [
                    "https://www.bilibili.com/video/BV19CwVz7EAU",
                    "--style",
                    "concise",
                    "--no-screenshot",
                ],
            )

        self.assertEqual(result.exit_code, 0)
        kwargs = note_generator_cls.return_value.return_value.generate.call_args.kwargs
        self.assertEqual(kwargs["style"], "concise")
        self.assertFalse(kwargs["screenshot"])
        self.assertEqual(kwargs["_format"], ["toc", "summary"])

    def test_cli_writes_markdown_to_explicit_output_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "note.md"
            with (
                patch("app.cli.note.initialize_runtime"),
                patch("app.cli.note.note_generator_class") as note_generator_cls,
            ):
                note_generator_cls.return_value.return_value.generate.return_value = self.fake_result

                result = self.runner.invoke(
                    app,
                    [
                        "https://www.bilibili.com/video/BV19CwVz7EAU",
                        "--output",
                        str(output_path),
                    ],
                )

            self.assertEqual(result.exit_code, 0)
            self.assertTrue(output_path.exists())
            self.assertEqual(output_path.read_text(encoding="utf-8"), "# test note\n")


if __name__ == "__main__":
    unittest.main()
