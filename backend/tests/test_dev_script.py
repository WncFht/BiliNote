import os
import subprocess
import tempfile
import time
import unittest
from pathlib import Path


class DevScriptTest(unittest.TestCase):
    def setUp(self) -> None:
        self.repo_root = Path(__file__).resolve().parents[2]
        self.script_path = self.repo_root / "scripts" / "dev.sh"
        self.temp_dir = tempfile.TemporaryDirectory()
        self.runtime_root = Path(self.temp_dir.name)
        self.backend_pid = self.runtime_root / "backend.pid"
        self.frontend_pid = self.runtime_root / "frontend.pid"
        self.backend_log = self.runtime_root / "backend.log"
        self.frontend_log = self.runtime_root / "frontend.log"
        self.backend_service = self._write_fake_service("backend")
        self.frontend_service = self._write_fake_service("frontend")

    def tearDown(self) -> None:
        try:
            self.run_script("stop")
        except FileNotFoundError:
            pass
        self.temp_dir.cleanup()

    def _write_fake_service(self, name: str) -> Path:
        script_path = self.runtime_root / f"{name}_service.sh"
        script_path.write_text(
            "\n".join(
                [
                    "#!/usr/bin/env bash",
                    "set -euo pipefail",
                    f'echo "{name}-ready"',
                    "trap 'exit 0' TERM INT",
                    "while true; do",
                    "  sleep 1",
                    "done",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        script_path.chmod(0o755)
        return script_path

    def wait_for(self, predicate, timeout: float = 5.0) -> None:
        deadline = time.time() + timeout
        while time.time() < deadline:
            if predicate():
                return
            time.sleep(0.1)
        self.fail("condition not met before timeout")

    def process_exists(self, pid: int) -> bool:
        try:
            os.kill(pid, 0)
        except OSError:
            return False
        return True

    def run_script(self, *args: str) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        env.update(
            {
                "BILINOTE_BACKEND_PID_FILE": str(self.backend_pid),
                "BILINOTE_FRONTEND_PID_FILE": str(self.frontend_pid),
                "BILINOTE_BACKEND_LOG_FILE": str(self.backend_log),
                "BILINOTE_FRONTEND_LOG_FILE": str(self.frontend_log),
                "BILINOTE_BACKEND_CMD": str(self.backend_service),
                "BILINOTE_FRONTEND_CMD": str(self.frontend_service),
                "BILINOTE_BACKEND_WORKDIR": str(self.runtime_root),
                "BILINOTE_FRONTEND_WORKDIR": str(self.runtime_root),
            }
        )
        return subprocess.run(
            [str(self.script_path), *args],
            check=False,
            capture_output=True,
            text=True,
            env=env,
        )

    def test_status_reports_stopped_when_pid_files_are_missing(self) -> None:
        result = self.run_script("status")

        self.assertEqual(result.returncode, 0)
        self.assertIn("backend: stopped", result.stdout)
        self.assertIn("frontend: stopped", result.stdout)

    def test_start_creates_pid_files_and_logs(self) -> None:
        result = self.run_script("start")

        self.assertEqual(result.returncode, 0)
        self.wait_for(lambda: self.backend_pid.exists() and self.frontend_pid.exists())
        self.wait_for(
            lambda: self.backend_log.exists()
            and self.frontend_log.exists()
            and "backend-ready" in self.backend_log.read_text(encoding="utf-8")
            and "frontend-ready" in self.frontend_log.read_text(encoding="utf-8")
        )

    def test_stop_removes_running_services(self) -> None:
        self.run_script("start")
        self.wait_for(lambda: self.backend_pid.exists() and self.frontend_pid.exists())
        backend_pid = int(self.backend_pid.read_text(encoding="utf-8").strip())
        frontend_pid = int(self.frontend_pid.read_text(encoding="utf-8").strip())

        result = self.run_script("stop")

        self.assertEqual(result.returncode, 0)
        self.wait_for(
            lambda: not self.backend_pid.exists()
            and not self.frontend_pid.exists()
            and not self.process_exists(backend_pid)
            and not self.process_exists(frontend_pid)
        )

    def test_restart_replaces_pid_files(self) -> None:
        self.run_script("start")
        self.wait_for(lambda: self.backend_pid.exists() and self.frontend_pid.exists())
        original_backend_pid = self.backend_pid.read_text(encoding="utf-8").strip()
        original_frontend_pid = self.frontend_pid.read_text(encoding="utf-8").strip()

        result = self.run_script("restart")

        self.assertEqual(result.returncode, 0)
        self.wait_for(
            lambda: self.backend_pid.exists()
            and self.frontend_pid.exists()
            and self.backend_pid.read_text(encoding="utf-8").strip() != original_backend_pid
            and self.frontend_pid.read_text(encoding="utf-8").strip() != original_frontend_pid
        )

    def test_logs_reads_recent_output(self) -> None:
        self.run_script("start")
        self.wait_for(
            lambda: self.backend_log.exists()
            and "backend-ready" in self.backend_log.read_text(encoding="utf-8")
        )

        result = self.run_script("logs", "backend")

        self.assertEqual(result.returncode, 0)
        self.assertIn("backend-ready", result.stdout)


if __name__ == "__main__":
    unittest.main()
