import tempfile
import unittest
from pathlib import Path

from app.gpt.prompt_builder import generate_base_prompt
from app.models.audio_model import AudioDownloadResult
from app.models.transcriber_model import TranscriptResult, TranscriptSegment
from app.services.note import NoteGenerator


class PromptMathDelimiterContractTest(unittest.TestCase):
    def test_generate_base_prompt_requires_dollar_math_delimiters(self) -> None:
        prompt = generate_base_prompt(
            title="测试视频",
            segment_text="00:00 - 测试内容",
            tags=["数学"],
        )

        self.assertIn("行内公式使用 `$...$`", prompt)
        self.assertIn("独立公式使用 `$$...$$`", prompt)
        self.assertIn("不要使用 `\\(...\\)` 或 `\\[...\\]`", prompt)


class NoteGeneratorMathDelimiterNormalizationTest(unittest.TestCase):
    def test_summarize_text_normalizes_latex_math_delimiters_before_writing(self) -> None:
        class FakeGPT:
            def summarize(self, source, progress_callback=None):
                return (
                    "行内公式：\\(a+b\\)\n\n"
                    "块公式：\n\\[\na^2+b^2=c^2\n\\]\n"
                )

        generator = NoteGenerator.__new__(NoteGenerator)
        generator._update_status = lambda task_id, status, message=None: None

        audio_meta = AudioDownloadResult(
            file_path="test.mp3",
            title="测试视频",
            duration=1.0,
            cover_url=None,
            platform="bilibili",
            video_id="BV1test",
            raw_info={"tags": ["数学"]},
        )
        transcript = TranscriptResult(
            language="zh",
            full_text="测试内容",
            segments=[TranscriptSegment(start=0.0, end=1.0, text="测试内容")],
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            markdown_cache_file = Path(temp_dir) / "task_markdown.md"
            markdown = generator._summarize_text(
                audio_meta=audio_meta,
                transcript=transcript,
                gpt=FakeGPT(),
                markdown_cache_file=markdown_cache_file,
                link=False,
                screenshot=False,
                formats=[],
                style="detailed",
                extras=None,
                video_img_urls=[],
            )

            written_markdown = markdown_cache_file.read_text(encoding="utf-8")

        expected = "行内公式：$a+b$\n\n块公式：\n$$\na^2+b^2=c^2\n$$\n"
        self.assertEqual(markdown, expected)
        self.assertEqual(written_markdown, expected)


if __name__ == "__main__":
    unittest.main()
