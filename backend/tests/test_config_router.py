import os
import unittest
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.routers.config import router


class ConfigRouterTest(unittest.TestCase):
    def test_deploy_status_gracefully_handles_missing_torch(self) -> None:
        app = FastAPI()
        app.include_router(router, prefix="/api")

        with (
            patch("app.routers.config._load_torch_module", return_value=None),
            patch("app.routers.config.ensure_ffmpeg_or_raise"),
            patch.object(
                __import__("app.routers.config", fromlist=["transcriber_config_manager"]).transcriber_config_manager,
                "get_config",
                return_value={"whisper_model_size": "base", "transcriber_type": "fast-whisper"},
            ),
            patch.dict(os.environ, {"BACKEND_PORT": "8484"}, clear=False),
        ):
            response = TestClient(app).get("/api/deploy_status")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["code"], 0)
        self.assertEqual(payload["data"]["backend"]["port"], 8484)
        self.assertFalse(payload["data"]["cuda"]["available"])
        self.assertIsNone(payload["data"]["cuda"]["version"])
        self.assertIsNone(payload["data"]["cuda"]["gpu_name"])


if __name__ == "__main__":
    unittest.main()
