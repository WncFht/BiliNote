import json
import tempfile
import subprocess
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from typer.testing import CliRunner

from app.models.audio_model import AudioDownloadResult
from app.models.notes_model import NoteResult
from app.models.transcriber_model import TranscriptResult
from app.cli.note import (
    app,
    extract_h1_title,
    generate_notes,
    resolve_output_path,
    sanitize_filename,
)


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
        self.assertIn("--jobs", result.stdout)
        self.assertIn("--manifest-json", result.stdout)
        self.assertIn("--progress-jsonl", result.stdout)
        self.assertIn("--continue-on-er", result.stdout)

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
        self.assertFalse(kwargs["screenshot"])
        self.assertFalse(kwargs["video_understanding"])
        self.assertEqual(kwargs["video_interval"], 4)
        self.assertEqual(kwargs["grid_size"], [])
        self.assertEqual(kwargs["_format"], ["toc", "summary"])

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
        self.assertFalse(kwargs["video_understanding"])
        self.assertEqual(kwargs["grid_size"], [])
        self.assertEqual(kwargs["_format"], ["toc", "summary"])

    def test_cli_allows_explicit_screenshot_mode(self) -> None:
        with (
            patch("app.cli.note.initialize_runtime"),
            patch("app.cli.note.note_generator_class") as note_generator_cls,
        ):
            note_generator_cls.return_value.return_value.generate.return_value = self.fake_result

            result = self.runner.invoke(
                app,
                [
                    "https://www.bilibili.com/video/BV19CwVz7EAU",
                    "--screenshot",
                ],
            )

        self.assertEqual(result.exit_code, 0)
        kwargs = note_generator_cls.return_value.return_value.generate.call_args.kwargs
        self.assertTrue(kwargs["screenshot"])
        self.assertTrue(kwargs["video_understanding"])
        self.assertEqual(kwargs["grid_size"], [3, 3])
        self.assertEqual(kwargs["_format"], ["toc", "summary", "screenshot"])

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
            titled_output_path = Path(temp_dir) / "test note.md"
            self.assertTrue(titled_output_path.exists())
            self.assertEqual(titled_output_path.read_text(encoding="utf-8"), "# test note\n")
            self.assertEqual(Path(result.stdout.strip()), titled_output_path)

    def test_cli_writes_markdown_to_default_obsidian_output_dir_when_output_omitted(self) -> None:
        expected_output_path = Path("/Users/fanghaotian/Desktop/obsidian/视频/test note.md")

        with (
            patch("app.cli.note.initialize_runtime"),
            patch("app.cli.note.note_generator_class") as note_generator_cls,
            patch("app.cli.note.write_markdown") as write_markdown,
        ):
            note_generator_cls.return_value.return_value.generate.return_value = self.fake_result
            write_markdown.return_value = expected_output_path

            result = self.runner.invoke(app, ["https://www.bilibili.com/video/BV19CwVz7EAU"])

        self.assertEqual(result.exit_code, 0)
        write_markdown.assert_called_once_with("# test note\n", expected_output_path)
        self.assertEqual(Path(result.stdout.strip()), expected_output_path)

    def test_cli_uses_video_title_when_markdown_h1_is_directory(self) -> None:
        toc_result = NoteResult(
            markdown="# 目录\n\n- item\n",
            transcript=TranscriptResult(language="zh", full_text="hello", segments=[]),
            audio_meta=AudioDownloadResult(
                file_path="test.mp3",
                title="真实视频标题",
                duration=1.0,
                cover_url=None,
                platform="bilibili",
                video_id="BV1toc",
                raw_info={},
            ),
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "note.md"
            with (
                patch("app.cli.note.initialize_runtime"),
                patch("app.cli.note.note_generator_class") as note_generator_cls,
            ):
                note_generator_cls.return_value.return_value.generate.return_value = toc_result

                result = self.runner.invoke(
                    app,
                    [
                        "https://www.bilibili.com/video/BV19CwVz7EAU",
                        "--output",
                        str(output_path),
                    ],
                )

            self.assertEqual(result.exit_code, 0)
            titled_output_path = Path(temp_dir) / "真实视频标题.md"
            self.assertTrue(titled_output_path.exists())
            self.assertEqual(Path(result.stdout.strip()), titled_output_path)

    def test_cli_processes_multiple_urls_with_jobs_and_prints_every_output_path(self) -> None:
        video_url_1 = "https://www.bilibili.com/video/BV19CwVz7EAU"
        video_url_2 = "https://www.bilibili.com/video/BV11UwDzzEMN"
        output_dir = Path("/tmp/batch-notes")
        expected_paths = {
            video_url_1: output_dir / "note-1.md",
            video_url_2: output_dir / "note-2.md",
        }

        def fake_generate_note(
            video_url: str,
            style: str,
            screenshot: bool,
            output: Path | None,
            batch_mode: bool = False,
            progress_callback=None,
        ) -> Path:
            del progress_callback
            self.assertEqual(style, "detailed")
            self.assertFalse(screenshot)
            self.assertEqual(output, output_dir)
            self.assertTrue(batch_mode)
            return expected_paths[video_url]

        with patch("app.cli.note.generate_note", side_effect=fake_generate_note) as generate_note:
            result = self.runner.invoke(
                app,
                [
                    video_url_1,
                    video_url_2,
                    "--jobs",
                    "2",
                    "--output",
                    str(output_dir),
                ],
            )

        self.assertEqual(result.exit_code, 0)
        self.assertEqual(
            result.stdout.strip().splitlines(),
            [str(expected_paths[video_url_1]), str(expected_paths[video_url_2])],
        )
        self.assertEqual(generate_note.call_count, 2)

    def test_cli_rejects_markdown_file_output_in_batch_mode(self) -> None:
        result = self.runner.invoke(
            app,
            [
                "https://www.bilibili.com/video/BV19CwVz7EAU",
                "https://www.bilibili.com/video/BV11UwDzzEMN",
                "--jobs",
                "2",
                "--output",
                "/tmp/custom-note.md",
            ],
        )

        self.assertEqual(result.exit_code, 2)
        self.assertIn("directory", result.output)

    def test_cli_writes_manifest_and_progress_for_batch_success(self) -> None:
        video_url_1 = "https://www.bilibili.com/video/BV19CwVz7EAU"
        video_url_2 = "https://www.bilibili.com/video/BV11UwDzzEMN"

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            output_dir = temp_root / "notes"
            manifest_path = temp_root / "manifest.json"
            progress_path = temp_root / "progress.jsonl"
            expected_paths = {
                video_url_1: output_dir / "BV19 note-1.md",
                video_url_2: output_dir / "BV11 note-2.md",
            }

            def fake_generate_note(*args, **kwargs):
                video_url = args[0]
                path = expected_paths[video_url]
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("# note\n", encoding="utf-8")
                return path

            with patch("app.cli.note.generate_note", side_effect=fake_generate_note):
                result = self.runner.invoke(
                    app,
                    [
                        video_url_1,
                        video_url_2,
                        "--jobs",
                        "2",
                        "--output",
                        str(output_dir),
                        "--manifest-json",
                        str(manifest_path),
                        "--progress-jsonl",
                        str(progress_path),
                    ],
                )

            self.assertEqual(result.exit_code, 0)
            self.assertTrue(manifest_path.exists())
            self.assertTrue(progress_path.exists())
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(manifest["total"], 2)
            self.assertEqual(manifest["success_count"], 2)
            self.assertEqual(manifest["failure_count"], 0)
            self.assertEqual(
                [item["status"] for item in manifest["items"]],
                ["success", "success"],
            )
            self.assertEqual(
                [item["output_path"] for item in manifest["items"]],
                [str(expected_paths[video_url_1]), str(expected_paths[video_url_2])],
            )
            events = [
                json.loads(line)
                for line in progress_path.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            self.assertIn("batch_started", {event["event"] for event in events})
            self.assertIn("batch_finished", {event["event"] for event in events})
            self.assertEqual(sum(event["event"] == "note_started" for event in events), 2)
            self.assertEqual(sum(event["event"] == "note_succeeded" for event in events), 2)

    def test_cli_writes_note_progress_heartbeat_events(self) -> None:
        video_url = "https://www.bilibili.com/video/BV19CwVz7EAU"

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            output_dir = temp_root / "notes"
            manifest_path = temp_root / "manifest.json"
            progress_path = temp_root / "progress.jsonl"
            expected_path = output_dir / "BV19 note-1.md"

            def fake_generate_note(*args, **kwargs):
                progress_callback = kwargs.get("progress_callback")
                if progress_callback is not None:
                    progress_callback("summarizing", "模型正在生成")
                expected_path.parent.mkdir(parents=True, exist_ok=True)
                expected_path.write_text("# note\n", encoding="utf-8")
                return expected_path

            with patch("app.cli.note.generate_note", side_effect=fake_generate_note):
                result = self.runner.invoke(
                    app,
                    [
                        video_url,
                        "--jobs",
                        "1",
                        "--output",
                        str(output_dir),
                        "--manifest-json",
                        str(manifest_path),
                        "--progress-jsonl",
                        str(progress_path),
                    ],
                )

            self.assertEqual(result.exit_code, 0)
            events = [
                json.loads(line)
                for line in progress_path.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            progress_events = [event for event in events if event["event"] == "note_progress"]
            self.assertEqual(len(progress_events), 1)
            self.assertEqual(progress_events[0]["video_url"], video_url)
            self.assertEqual(progress_events[0]["status"], "summarizing")
            self.assertEqual(progress_events[0]["message"], "模型正在生成")

    def test_generate_notes_only_marks_running_items_as_started(self) -> None:
        video_url_1 = "https://www.bilibili.com/video/BV19CwVz7EAU"
        video_url_2 = "https://www.bilibili.com/video/BV11UwDzzEMN"

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            output_dir = temp_root / "notes"
            manifest_path = temp_root / "manifest.json"
            progress_path = temp_root / "progress.jsonl"
            first_started = threading.Event()
            release_first = threading.Event()
            summary_holder: dict[str, object] = {}
            worker_errors: list[BaseException] = []

            def fake_generate_note(*args, **kwargs):
                del kwargs
                video_url = args[0]
                if video_url == video_url_1:
                    first_started.set()
                    self.assertTrue(release_first.wait(timeout=1))
                output_path = output_dir / f"{Path(video_url).name}.md"
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_text("# note\n", encoding="utf-8")
                return output_path

            def run_batch() -> None:
                try:
                    summary_holder["summary"] = generate_notes(
                        video_urls=[video_url_1, video_url_2],
                        style="detailed",
                        screenshot=False,
                        output=output_dir,
                        jobs=1,
                        manifest_json=manifest_path,
                        progress_jsonl=progress_path,
                    )
                except BaseException as exc:  # pragma: no cover - failure path inspected by test
                    worker_errors.append(exc)

            with (
                patch("app.cli.note.initialize_runtime"),
                patch("app.cli.note.generate_note", side_effect=fake_generate_note),
            ):
                worker = threading.Thread(target=run_batch)
                worker.start()
                self.assertTrue(first_started.wait(timeout=1))
                time.sleep(0.05)
                progress_events = [
                    json.loads(line)
                    for line in progress_path.read_text(encoding="utf-8").splitlines()
                    if line.strip()
                ]
                self.assertEqual(
                    [event["video_url"] for event in progress_events if event["event"] == "note_started"],
                    [video_url_1],
                )
                release_first.set()
                worker.join(timeout=1)

            self.assertFalse(worker.is_alive())
            self.assertEqual(worker_errors, [])
            summary = summary_holder["summary"]
            self.assertEqual(len(summary.output_paths), 2)

    def test_cli_continue_on_error_writes_manifest_with_partial_success(self) -> None:
        video_url_1 = "https://www.bilibili.com/video/BV19CwVz7EAU"
        video_url_2 = "https://www.bilibili.com/video/BV11UwDzzEMN"

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            output_dir = temp_root / "notes"
            manifest_path = temp_root / "manifest.json"
            progress_path = temp_root / "progress.jsonl"
            success_path = output_dir / "BV19 note-1.md"

            def fake_generate_note(*args, **kwargs):
                video_url = args[0]
                if video_url == video_url_2:
                    raise RuntimeError("boom")
                success_path.parent.mkdir(parents=True, exist_ok=True)
                success_path.write_text("# note\n", encoding="utf-8")
                return success_path

            with patch("app.cli.note.generate_note", side_effect=fake_generate_note):
                result = self.runner.invoke(
                    app,
                    [
                        video_url_1,
                        video_url_2,
                        "--jobs",
                        "2",
                        "--output",
                        str(output_dir),
                        "--manifest-json",
                        str(manifest_path),
                        "--progress-jsonl",
                        str(progress_path),
                        "--continue-on-error",
                    ],
                )

            self.assertEqual(result.exit_code, 1)
            self.assertTrue(manifest_path.exists())
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(manifest["success_count"], 1)
            self.assertEqual(manifest["failure_count"], 1)
            self.assertEqual(
                [item["status"] for item in manifest["items"]],
                ["success", "failed"],
            )
            self.assertEqual(manifest["items"][0]["output_path"], str(success_path))
            self.assertEqual(manifest["items"][1]["error"], "boom")

    def test_resolve_output_path_uses_h1_title_and_sanitizes_filename(self) -> None:
        output_path = resolve_output_path(
            markdown='# Hello: "World" / test?\n\nbody',
            output=Path("/tmp/custom-name.md"),
            fallback_stem="BV1test",
        )

        self.assertEqual(output_path, Path("/tmp/Hello World test.md"))

    def test_resolve_output_path_uses_preferred_stem_when_h1_is_directory(self) -> None:
        output_path = resolve_output_path(
            markdown="# 目录\n\n- item",
            output=Path("/tmp/custom-name.md"),
            fallback_stem="BV1test",
            preferred_stem="真实视频标题",
        )

        self.assertEqual(output_path, Path("/tmp/真实视频标题.md"))

    def test_extract_h1_title_returns_none_when_markdown_has_no_h1(self) -> None:
        self.assertIsNone(extract_h1_title("## subtitle\ncontent"))

    def test_sanitize_filename_falls_back_when_title_becomes_empty(self) -> None:
        self.assertEqual(sanitize_filename('\\\\/:*?\"<>|'), "")


if __name__ == "__main__":
    unittest.main()
