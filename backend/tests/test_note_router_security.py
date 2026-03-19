import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from app.routers.note import (
    build_safe_upload_name,
    get_task_status,
    validate_image_proxy_url,
)
from app.utils.response import ResponseWrapper


class NoteRouterSecurityTest(unittest.TestCase):
    def test_build_safe_upload_name_strips_path_segments_and_randomizes_result(self) -> None:
        with patch("app.routers.note.uuid.uuid4", return_value=SimpleNamespace(hex="safeid123")):
            safe_name = build_safe_upload_name("../nested\\evil file?.png")

        self.assertEqual(safe_name, "safeid123-evil_file_.png")
        self.assertNotIn("/", safe_name)
        self.assertNotIn("\\", safe_name)

    def test_validate_image_proxy_url_rejects_private_hosts(self) -> None:
        with self.assertRaises(ValueError):
            validate_image_proxy_url("http://127.0.0.1:8000/secret.png")

    def test_error_wrapper_sets_http_status_code(self) -> None:
        response = ResponseWrapper.error(msg="boom", code=500)

        self.assertEqual(response.status_code, 500)
        self.assertEqual(json.loads(response.body), {
            "code": 500,
            "msg": "boom",
            "data": None,
        })

    def test_task_status_failed_response_uses_http_500(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            status_file = Path(temp_dir) / "task-1.status.json"
            status_file.write_text(
                json.dumps({"status": "FAILED", "message": "任务失败"}),
                encoding="utf-8",
            )

            with patch("app.routers.note.NOTE_OUTPUT_DIR", temp_dir):
                response = get_task_status("task-1")

        self.assertEqual(response.status_code, 500)
        self.assertEqual(json.loads(response.body), {
            "code": 500,
            "msg": "任务失败",
            "data": None,
        })


if __name__ == "__main__":
    unittest.main()
