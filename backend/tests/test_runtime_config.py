import os
import unittest
from pathlib import Path
from unittest.mock import patch


class RuntimeConfigTest(unittest.TestCase):
    def test_sync_provider_from_env_updates_openai_provider(self) -> None:
        with (
            patch.dict(
                os.environ,
                {
                    "OPENAI_API_KEY": "sk-test",
                    "OPENAI_API_BASE_URL": "http://127.0.0.1:23000/v1",
                },
                clear=False,
            ),
            patch("app.runtime_config.get_provider_by_id", return_value=object()),
            patch("app.runtime_config.update_provider") as update_provider,
        ):
            from app.runtime_config import sync_provider_from_env

            changed = sync_provider_from_env(
                provider_id="openai",
                api_key_env_var="OPENAI_API_KEY",
                base_url_env_var="OPENAI_API_BASE_URL",
            )

        self.assertTrue(changed)
        update_provider.assert_called_once_with(
            "openai",
            api_key="sk-test",
            base_url="http://127.0.0.1:23000/v1",
        )

    def test_initialize_backend_runtime_loads_env_and_syncs_openai_provider(self) -> None:
        with (
            patch("app.runtime_config.load_dotenv") as load_dotenv_mock,
            patch("app.runtime_config.init_db") as init_db,
            patch("app.runtime_config.seed_default_providers") as seed_default_providers,
            patch("app.runtime_config.sync_provider_from_env") as sync_provider_from_env,
        ):
            from app.runtime_config import initialize_backend_runtime

            initialize_backend_runtime(Path("/tmp/backend/.env"))

        load_dotenv_mock.assert_called_once_with(Path("/tmp/backend/.env"), override=True)
        init_db.assert_called_once()
        seed_default_providers.assert_called_once()
        sync_provider_from_env.assert_called_once_with(
            provider_id="openai",
            api_key_env_var="OPENAI_API_KEY",
            base_url_env_var="OPENAI_API_BASE_URL",
        )


if __name__ == "__main__":
    unittest.main()
