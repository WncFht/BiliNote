from datetime import timedelta
from typing import Callable, List, Optional

from app.gpt.base import GPT
from app.gpt.prompt_builder import generate_base_prompt
from app.models.gpt_model import GPTSource
from app.models.transcriber_model import TranscriptSegment


class UniversalGPT(GPT):
    def __init__(self, client, model: str, temperature: float = 0.7):
        self.client = client
        self.model = model
        self.temperature = temperature
        self.screenshot = False
        self.link = False

    def _format_time(self, seconds: float) -> str:
        return str(timedelta(seconds=int(seconds)))[2:]

    def _build_segment_text(self, segments: List[TranscriptSegment]) -> str:
        return "\n".join(
            f"{self._format_time(seg.start)} - {seg.text.strip()}"
            for seg in segments
        )

    def ensure_segments_type(self, segments) -> List[TranscriptSegment]:
        return [TranscriptSegment(**seg) if isinstance(seg, dict) else seg for seg in segments]

    def create_input(self, segments: List[TranscriptSegment], **kwargs):
        content_text = generate_base_prompt(
            title=kwargs.get('title'),
            segment_text=self._build_segment_text(segments),
            tags=kwargs.get('tags'),
            _format=kwargs.get('_format'),
            style=kwargs.get('style'),
            extras=kwargs.get('extras'),
        )

        content = [{"type": "input_text", "text": content_text}]
        video_img_urls = kwargs.get('video_img_urls') or []

        for url in video_img_urls:
            content.append({
                "type": "input_image",
                "image_url": url,
                "detail": "auto",
            })

        return [{
            "role": "user",
            "content": content,
        }]

    def create_messages(self, segments: List[TranscriptSegment], **kwargs):
        return self.create_input(segments, **kwargs)

    def list_models(self):
        return self.client.models.list()

    def _emit_progress(
        self,
        progress_callback: Optional[Callable[[str], None]],
        message: str,
    ) -> None:
        if progress_callback:
            progress_callback(message)

    def _extract_response_text(self, response) -> str:
        output_text = getattr(response, "output_text", None)
        if output_text:
            return output_text.strip()

        parts = []
        for item in getattr(response, "output", []) or []:
            for content in getattr(item, "content", []) or []:
                text = getattr(content, "text", None)
                if text:
                    parts.append(text)
        return "".join(parts).strip()

    def _summarize_with_responses_stream(
        self,
        response_input,
        progress_callback: Optional[Callable[[str], None]] = None,
    ) -> str:
        chunks = []
        generated_chars = 0
        last_reported_chars = 0

        self._emit_progress(progress_callback, "总结中：已连接响应流")
        with self.client.responses.stream(
            model=self.model,
            input=response_input,
            temperature=self.temperature,
        ) as stream:
            for event in stream:
                event_type = getattr(event, "type", "")
                if event_type == "response.in_progress":
                    self._emit_progress(progress_callback, "总结中：模型正在生成")
                    continue

                if event_type == "response.output_text.delta":
                    delta = getattr(event, "delta", "")
                    if not delta:
                        continue

                    chunks.append(delta)
                    generated_chars += len(delta)
                    if generated_chars - last_reported_chars >= 400:
                        last_reported_chars = generated_chars
                        self._emit_progress(
                            progress_callback,
                            f"总结中：已生成约 {generated_chars} 字",
                        )
                    continue

                if event_type == "response.completed":
                    self._emit_progress(progress_callback, "总结中：响应完成")

            try:
                final_response = stream.get_final_response()
            except Exception:
                final_text = "".join(chunks).strip()
                if final_text:
                    return final_text
                raise

        final_text = "".join(chunks).strip()
        if final_text:
            return final_text
        return self._extract_response_text(final_response)

    def _summarize_with_responses_create(
        self,
        response_input,
        progress_callback: Optional[Callable[[str], None]] = None,
    ) -> str:
        self._emit_progress(progress_callback, "总结中：已发送响应请求")
        response = self.client.responses.create(
            model=self.model,
            input=response_input,
            temperature=self.temperature,
        )
        self._emit_progress(progress_callback, "总结中：响应完成")
        return self._extract_response_text(response)

    def summarize(
        self,
        source: GPTSource,
        progress_callback: Optional[Callable[[str], None]] = None,
    ) -> str:
        self.screenshot = source.screenshot
        self.link = source.link
        source.segment = self.ensure_segments_type(source.segment)

        response_input = self.create_input(
            source.segment,
            title=source.title,
            tags=source.tags,
            video_img_urls=source.video_img_urls,
            _format=source._format,
            style=source.style,
            extras=source.extras
        )

        try:
            return self._summarize_with_responses_stream(
                response_input=response_input,
                progress_callback=progress_callback,
            )
        except Exception:
            return self._summarize_with_responses_create(
                response_input=response_input,
                progress_callback=progress_callback,
            )
