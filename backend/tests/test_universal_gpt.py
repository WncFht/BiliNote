import tempfile
import unittest
from types import SimpleNamespace
from pathlib import Path

from app.gpt.universal_gpt import UniversalGPT
from app.enmus.task_status_enums import TaskStatus
from app.models.audio_model import AudioDownloadResult
from app.models.gpt_model import GPTSource
from app.models.transcriber_model import TranscriptSegment
from app.models.transcriber_model import TranscriptResult
from app.services.note import NoteGenerator


class FakeResponsesStream:
    def __init__(self, events, final_text: str):
        self._events = events
        self._final_text = final_text

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def __iter__(self):
        return iter(self._events)

    def get_final_response(self):
        return SimpleNamespace(output_text=self._final_text)


class FakeResponsesAPI:
    def __init__(self, stream=None, create_response=None):
        self._stream = stream
        self._create_response = create_response
        self.stream_calls = []
        self.create_calls = []

    def stream(self, **kwargs):
        self.stream_calls.append(kwargs)
        if isinstance(self._stream, Exception):
            raise self._stream
        return self._stream

    def create(self, **kwargs):
        self.create_calls.append(kwargs)
        if isinstance(self._create_response, Exception):
            raise self._create_response
        return self._create_response


class FakeClient:
    def __init__(self, responses):
        self.responses = responses


class UniversalGPTResponsesTest(unittest.TestCase):
    def setUp(self) -> None:
        self.segment = [
            TranscriptSegment(start=3.0, end=6.0, text="测试内容"),
        ]

    def test_create_input_uses_responses_content_types(self) -> None:
        gpt = UniversalGPT(client=FakeClient(responses=None), model="gpt-5.4")

        response_input = gpt.create_input(
            self.segment,
            title="测试视频",
            tags=["AI", "B站"],
            video_img_urls=["https://example.com/frame.jpg"],
            _format=["toc", "summary", "screenshot"],
            style="detailed",
            extras=None,
        )

        self.assertEqual(len(response_input), 1)
        self.assertEqual(response_input[0]["role"], "user")
        self.assertEqual(response_input[0]["content"][0]["type"], "input_text")
        self.assertIn("测试视频", response_input[0]["content"][0]["text"])
        self.assertEqual(
            response_input[0]["content"][1],
            {
                "type": "input_image",
                "image_url": "https://example.com/frame.jpg",
                "detail": "auto",
            },
        )

    def test_summarize_streams_responses_and_reports_progress(self) -> None:
        events = [
            SimpleNamespace(type="response.created"),
            SimpleNamespace(type="response.in_progress"),
            SimpleNamespace(type="response.output_text.delta", delta="第一段"),
            SimpleNamespace(type="response.output_text.delta", delta="第二段"),
            SimpleNamespace(type="response.completed"),
        ]
        responses_api = FakeResponsesAPI(
            stream=FakeResponsesStream(events, final_text="第一段第二段"),
        )
        gpt = UniversalGPT(client=FakeClient(responses=responses_api), model="gpt-5.4")
        progress_messages = []

        markdown = gpt.summarize(
            GPTSource(
                segment=self.segment,
                title="测试视频",
                tags=["AI"],
                screenshot=True,
                style="detailed",
                _format=["summary"],
                video_img_urls=["https://example.com/frame.jpg"],
            ),
            progress_callback=progress_messages.append,
        )

        self.assertEqual(markdown, "第一段第二段")
        self.assertTrue(responses_api.stream_calls)
        self.assertEqual(progress_messages[0], "总结中：已连接响应流")
        self.assertIn("总结中：模型正在生成", progress_messages)
        self.assertEqual(progress_messages[-1], "总结中：响应完成")

    def test_summarize_uses_final_response_text_when_no_deltas_arrive(self) -> None:
        responses_api = FakeResponsesAPI(
            stream=FakeResponsesStream(
                [SimpleNamespace(type="response.completed")],
                final_text="最终答案",
            ),
        )
        gpt = UniversalGPT(client=FakeClient(responses=responses_api), model="gpt-5.4")

        markdown = gpt.summarize(
            GPTSource(
                segment=self.segment,
                title="测试视频",
                tags=[],
            )
        )

        self.assertEqual(markdown, "最终答案")

    def test_note_generator_forwards_summarize_progress_to_status_updates(self) -> None:
        class FakeGPT:
            def summarize(self, source, progress_callback=None):
                progress_callback("总结中：模型正在生成")
                return "# 笔记"

        generator = NoteGenerator.__new__(NoteGenerator)
        status_updates = []
        generator._update_status = lambda task_id, status, message=None: status_updates.append((task_id, status, message))

        audio_meta = AudioDownloadResult(
            file_path="test.mp3",
            title="测试视频",
            duration=1.0,
            cover_url=None,
            platform="bilibili",
            video_id="BV1test",
            raw_info={"tags": ["AI"]},
        )
        transcript = TranscriptResult(language="zh", full_text="测试内容", segments=self.segment)

        with tempfile.TemporaryDirectory() as temp_dir:
            markdown_cache_file = Path(temp_dir) / "task_markdown.md"
            markdown = generator._summarize_text(
                audio_meta=audio_meta,
                transcript=transcript,
                gpt=FakeGPT(),
                markdown_cache_file=markdown_cache_file,
                link=False,
                screenshot=False,
                formats=["summary"],
                style="detailed",
                extras=None,
                video_img_urls=[],
            )

        self.assertEqual(markdown, "# 笔记")
        self.assertIn(
            ("task_markdown", TaskStatus.SUMMARIZING, "总结中：模型正在生成"),
            status_updates,
        )


if __name__ == "__main__":
    unittest.main()
