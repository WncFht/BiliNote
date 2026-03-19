import unittest
from unittest.mock import patch

from app.enmus.note_enums import DownloadQuality
from app.routers.note import run_note_task


class NoteRouterWebDefaultsTest(unittest.TestCase):
    def test_run_note_task_disables_image_input_for_web_requests(self) -> None:
        with patch("app.routers.note.NoteGenerator") as note_generator_cls:
            note_generator_cls.return_value.generate.return_value = None

            run_note_task(
                task_id="task-123",
                video_url="https://www.bilibili.com/video/BV19CwVz7EAU",
                platform="bilibili",
                quality=DownloadQuality.medium,
                link=True,
                screenshot=True,
                model_name="gpt-5.4",
                provider_id="openai",
                _format=["toc", "summary", "screenshot"],
                style="detailed",
                extras="keep links only",
                video_understanding=True,
                video_interval=4,
                grid_size=[3, 3],
            )

        kwargs = note_generator_cls.return_value.generate.call_args.kwargs
        self.assertFalse(kwargs["screenshot"])
        self.assertFalse(kwargs["video_understanding"])
        self.assertEqual(kwargs["_format"], ["toc", "summary"])
        self.assertEqual(kwargs["grid_size"], [])
        self.assertTrue(kwargs["link"])
        self.assertEqual(kwargs["style"], "detailed")


if __name__ == "__main__":
    unittest.main()
