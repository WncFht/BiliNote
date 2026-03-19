import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from app.routers.note import get_task_history, serialize_task_history_entry


class NoteHistoryTest(unittest.TestCase):
    def test_serialize_task_history_entry_reads_result_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            result_file = Path(temp_dir) / "task-1.json"
            result_file.write_text(
                json.dumps(
                    {
                        "markdown": "# Title",
                        "transcript": {
                            "full_text": "hello",
                            "language": "zh",
                            "raw": None,
                            "segments": [],
                        },
                        "audio_meta": {
                            "cover_url": "https://example.com/cover.jpg",
                            "duration": 12,
                            "file_path": "/tmp/audio.mp3",
                            "platform": "bilibili",
                            "raw_info": {},
                            "title": "Example title",
                            "video_id": "BV1",
                        },
                    }
                ),
                encoding="utf-8",
            )
            task_row = SimpleNamespace(
                task_id="task-1",
                platform="bilibili",
                created_at=datetime(2026, 3, 19, 18, 20, 0),
            )

            with patch("app.routers.note.NOTE_OUTPUT_DIR", temp_dir):
                payload = serialize_task_history_entry(task_row)

        self.assertEqual(payload["task_id"], "task-1")
        self.assertEqual(payload["status"], "SUCCESS")
        self.assertEqual(payload["result"]["markdown"], "# Title")
        self.assertEqual(payload["result"]["audio_meta"]["title"], "Example title")
        self.assertEqual(payload["created_at"], "2026-03-19T18:20:00")

    def test_get_task_history_returns_latest_tasks(self) -> None:
        task_rows = [
            SimpleNamespace(
                task_id="task-1",
                platform="bilibili",
                created_at=datetime(2026, 3, 19, 18, 20, 0),
            ),
            SimpleNamespace(
                task_id="task-2",
                platform="youtube",
                created_at=datetime(2026, 3, 19, 18, 10, 0),
            ),
        ]

        with tempfile.TemporaryDirectory() as temp_dir:
            (Path(temp_dir) / "task-2.status.json").write_text(
                json.dumps({"status": "FAILED", "message": "boom"}),
                encoding="utf-8",
            )

            with patch("app.routers.note.list_video_tasks", return_value=task_rows), patch(
                "app.routers.note.NOTE_OUTPUT_DIR", temp_dir
            ):
                response = get_task_history(limit=2)

        payload = json.loads(response.body)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(payload["data"]), 2)
        self.assertEqual(payload["data"][0]["task_id"], "task-1")
        self.assertEqual(payload["data"][1]["task_id"], "task-2")
        self.assertEqual(payload["data"][1]["status"], "FAILED")
        self.assertEqual(payload["data"][1]["message"], "boom")


if __name__ == "__main__":
    unittest.main()
