import unittest
from types import SimpleNamespace

from app.gpt.universal_gpt import UniversalGPT
from app.models.gpt_model import GPTSource
from app.models.transcriber_model import TranscriptSegment


class FakeResponsesStreamWithFinalError:
    def __init__(self, events, final_error: Exception):
        self._events = events
        self._final_error = final_error

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def __iter__(self):
        return iter(self._events)

    def get_final_response(self):
        raise self._final_error


class FakeResponsesAPI:
    def __init__(self, stream=None, create_response=None):
        self._stream = stream
        self._create_response = create_response
        self.stream_calls = []
        self.create_calls = []

    def stream(self, **kwargs):
        self.stream_calls.append(kwargs)
        return self._stream

    def create(self, **kwargs):
        self.create_calls.append(kwargs)
        return self._create_response


class FakeClient:
    def __init__(self, responses):
        self.responses = responses


class UniversalGPTStreamRegressionTest(unittest.TestCase):
    def test_summarize_keeps_streamed_chunks_when_final_response_lookup_fails(self) -> None:
        events = [
            SimpleNamespace(type="response.in_progress"),
            SimpleNamespace(type="response.output_text.delta", delta="第一段"),
            SimpleNamespace(type="response.output_text.delta", delta="第二段"),
            SimpleNamespace(type="response.completed"),
        ]
        responses_api = FakeResponsesAPI(
            stream=FakeResponsesStreamWithFinalError(
                events=events,
                final_error=RuntimeError("final response unavailable"),
            ),
            create_response=SimpleNamespace(output_text=""),
        )
        gpt = UniversalGPT(client=FakeClient(responses=responses_api), model="gpt-5.4")

        markdown = gpt.summarize(
            GPTSource(
                segment=[TranscriptSegment(start=0.0, end=1.0, text="测试内容")],
                title="测试视频",
                tags=[],
            )
        )

        self.assertEqual(markdown, "第一段第二段")
        self.assertEqual(responses_api.create_calls, [])


if __name__ == "__main__":
    unittest.main()
