import hashlib
import json
import os
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable, List, Optional

from app.gpt.base import GPT
from app.gpt.prompt_builder import generate_base_prompt
from app.gpt.request_chunker import RequestChunker
from app.models.gpt_model import GPTSource
from app.models.transcriber_model import TranscriptSegment


class UniversalGPT(GPT):
    def __init__(self, client, model: str, temperature: float = 0.7):
        self.client = client
        self.model = model
        self.temperature = temperature
        self.screenshot = False
        self.link = False
        self.max_request_bytes = int(os.getenv('OPENAI_MAX_REQUEST_BYTES', str(45 * 1024 * 1024)))
        self.checkpoint_dir = Path(os.getenv('NOTE_OUTPUT_DIR', 'note_results'))
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        self._max_retry_attempts = max(1, int(os.getenv('OPENAI_RETRY_ATTEMPTS', '3')))
        self._retry_base_backoff = float(os.getenv('OPENAI_RETRY_BACKOFF_SECONDS', '1.5'))

    def _format_time(self, seconds: float) -> str:
        return str(timedelta(seconds=int(seconds)))[2:]

    def _build_segment_text(self, segments: List[TranscriptSegment]) -> str:
        return '\n'.join(f'{self._format_time(seg.start)} - {seg.text.strip()}' for seg in segments)

    def ensure_segments_type(self, segments) -> List[TranscriptSegment]:
        return [TranscriptSegment(**seg) if isinstance(seg, dict) else seg for seg in segments]

    def _build_prompt(self, segments: List[TranscriptSegment], **kwargs) -> str:
        return generate_base_prompt(
            title=kwargs.get('title'),
            segment_text=self._build_segment_text(segments),
            tags=kwargs.get('tags'),
            _format=kwargs.get('_format'),
            style=kwargs.get('style'),
            extras=kwargs.get('extras'),
        )

    def create_input(self, segments: List[TranscriptSegment], **kwargs):
        content = [{'type': 'input_text', 'text': self._build_prompt(segments, **kwargs)}]
        for url in kwargs.get('video_img_urls') or []:
            content.append({
                'type': 'input_image',
                'image_url': url,
                'detail': 'auto',
            })

        return [{
            'role': 'user',
            'content': content,
        }]

    def create_messages(self, segments: List[TranscriptSegment], **kwargs):
        content = [{'type': 'text', 'text': self._build_prompt(segments, **kwargs)}]
        for url in kwargs.get('video_img_urls') or []:
            content.append({
                'type': 'image_url',
                'image_url': {
                    'url': url,
                    'detail': 'auto',
                },
            })

        return [{
            'role': 'user',
            'content': content,
        }]

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
        output_text = getattr(response, 'output_text', None)
        if output_text:
            return output_text.strip()

        parts = []
        for item in getattr(response, 'output', []) or []:
            for content in getattr(item, 'content', []) or []:
                text = getattr(content, 'text', None)
                if text:
                    parts.append(text)
        return ''.join(parts).strip()

    def _summarize_with_responses_stream(
        self,
        response_input,
        progress_callback: Optional[Callable[[str], None]] = None,
    ) -> str:
        chunks = []
        generated_chars = 0
        last_reported_chars = 0

        self._emit_progress(progress_callback, '总结中：已连接响应流')
        with self.client.responses.stream(
            model=self.model,
            input=response_input,
            temperature=self.temperature,
        ) as stream:
            for event in stream:
                event_type = getattr(event, 'type', '')
                if event_type == 'response.in_progress':
                    self._emit_progress(progress_callback, '总结中：模型正在生成')
                    continue

                if event_type == 'response.output_text.delta':
                    delta = getattr(event, 'delta', '')
                    if not delta:
                        continue

                    chunks.append(delta)
                    generated_chars += len(delta)
                    if generated_chars - last_reported_chars >= 400:
                        last_reported_chars = generated_chars
                        self._emit_progress(progress_callback, f'总结中：已生成约 {generated_chars} 字')
                    continue

                if event_type == 'response.completed':
                    self._emit_progress(progress_callback, '总结中：响应完成')

            try:
                final_response = stream.get_final_response()
            except Exception:
                final_text = ''.join(chunks).strip()
                if final_text:
                    return final_text
                raise

        final_text = ''.join(chunks).strip()
        if final_text:
            return final_text
        return self._extract_response_text(final_response)

    def _summarize_with_responses_create(
        self,
        response_input,
        progress_callback: Optional[Callable[[str], None]] = None,
    ) -> str:
        self._emit_progress(progress_callback, '总结中：已发送响应请求')
        response = self.client.responses.create(
            model=self.model,
            input=response_input,
            temperature=self.temperature,
        )
        self._emit_progress(progress_callback, '总结中：响应完成')
        return self._extract_response_text(response)

    def _estimate_messages_bytes(self, messages: list) -> int:
        return len(json.dumps(messages, ensure_ascii=False).encode('utf-8'))

    def _build_merge_messages(self, partials: list) -> list:
        merge_text = (
            '你将收到多个来自同一视频的 Markdown 笔记片段，请合并成一份完整笔记：\n'
            '- 只做合并与去重，不要发明新内容\n'
            '- 保持原有标题层级与 Markdown 结构\n'
            '- 保留所有 *Content-[mm:ss] 与 *Screenshot-[mm:ss] 标记\n'
            '- 保持中文输出，专有名词保留英文\n'
            '- 不要使用代码块包裹输出\n\n'
            + '\n\n---\n\n'.join(partials)
        )
        return [{
            'role': 'user',
            'content': [{'type': 'text', 'text': merge_text}],
        }]

    def _checkpoint_path(self, checkpoint_key: str) -> Path:
        safe_key = ''.join(ch if ch.isalnum() or ch in ('-', '_') else '_' for ch in checkpoint_key)
        return self.checkpoint_dir / f'{safe_key}.gpt.checkpoint.json'

    def _build_source_signature(self, source: GPTSource) -> str:
        payload = {
            'model': self.model,
            'temperature': self.temperature,
            'max_request_bytes': self.max_request_bytes,
            'title': source.title,
            'tags': source.tags,
            'format': source._format,
            'style': source.style,
            'extras': source.extras,
            'video_img_urls': source.video_img_urls or [],
            'segments': [
                {
                    'start': getattr(seg, 'start', None),
                    'end': getattr(seg, 'end', None),
                    'text': getattr(seg, 'text', ''),
                }
                for seg in source.segment
            ],
        }
        raw = json.dumps(payload, ensure_ascii=False, sort_keys=True)
        return hashlib.sha256(raw.encode('utf-8')).hexdigest()

    def _load_checkpoint(self, checkpoint_key: str, source_signature: str) -> dict | None:
        path = self._checkpoint_path(checkpoint_key)
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text(encoding='utf-8'))
            if data.get('source_signature') != source_signature:
                path.unlink(missing_ok=True)
                return None
            return data
        except Exception:
            path.unlink(missing_ok=True)
            return None

    def _save_checkpoint(self, checkpoint_key: str, source_signature: str, partials: list, phase: str) -> None:
        path = self._checkpoint_path(checkpoint_key)
        data = {
            'version': 1,
            'source_signature': source_signature,
            'phase': phase,
            'partials': partials,
            'updated_at': datetime.now(timezone.utc).isoformat(),
        }
        tmp_path = path.with_suffix('.tmp')
        tmp_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
        tmp_path.replace(path)

    def _clear_checkpoint(self, checkpoint_key: str) -> None:
        self._checkpoint_path(checkpoint_key).unlink(missing_ok=True)

    @staticmethod
    def _is_retryable_error(exc: Exception) -> bool:
        raw = str(exc).lower()
        retryable_tokens = (
            'error code: 524',
            'bad_response_status_code',
            'timed out',
            'timeout',
            'rate limit',
            'error code: 429',
            'error code: 500',
            'error code: 502',
            'error code: 503',
            'error code: 504',
            'apiconnectionerror',
            'connection error',
            'service unavailable',
        )
        if any(token in raw for token in retryable_tokens):
            return True

        status = getattr(exc, 'status_code', None) or getattr(exc, 'status', None)
        return status in {408, 409, 429, 500, 502, 503, 504, 524}

    def _chat_completion_create(self, messages: list):
        last_exc = None
        for attempt in range(self._max_retry_attempts):
            try:
                return self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=self.temperature,
                )
            except Exception as exc:
                last_exc = exc
                if attempt == self._max_retry_attempts - 1 or not self._is_retryable_error(exc):
                    raise
                time.sleep(self._retry_base_backoff * (2 ** attempt))

        if last_exc is not None:
            raise last_exc
        raise RuntimeError('chat completion failed without exception')

    def _extract_chat_completion_text(self, response) -> str:
        choice = response.choices[0]
        message = getattr(choice, 'message', None)
        content = getattr(message, 'content', '')
        if isinstance(content, list):
            return ''.join(
                part.get('text', '') if isinstance(part, dict) else str(part)
                for part in content
            ).strip()
        return str(content or '').strip()

    def _merge_partials(
        self,
        partials: list,
        checkpoint_key: str | None = None,
        source_signature: str | None = None,
        progress_callback: Optional[Callable[[str], None]] = None,
    ) -> str:
        def build_messages(texts, *_args, **_kwargs):
            return self._build_merge_messages(texts)

        merge_chunker = RequestChunker(
            lambda *_args, **_kwargs: [],
            self.max_request_bytes,
            self._estimate_messages_bytes,
        )

        current_partials = list(partials)
        while len(current_partials) > 1:
            groups = merge_chunker.group_texts_by_budget(current_partials, build_messages)
            new_partials = []
            for group_idx, group in enumerate(groups):
                self._emit_progress(progress_callback, f'总结中：正在合并分片 {group_idx + 1}/{len(groups)}')
                messages = build_messages(group)
                try:
                    response = self._chat_completion_create(messages)
                except Exception:
                    if checkpoint_key and source_signature:
                        self._save_checkpoint(checkpoint_key, source_signature, current_partials, 'merge')
                    raise

                new_partials.append(self._extract_chat_completion_text(response))

                if checkpoint_key and source_signature:
                    remaining_partials = []
                    for remaining_group in groups[group_idx + 1:]:
                        remaining_partials.extend(remaining_group)
                    resumable_partials = new_partials + remaining_partials
                    self._save_checkpoint(checkpoint_key, source_signature, resumable_partials, 'merge')

            current_partials = new_partials

        return current_partials[0]

    def _build_chunker(self) -> RequestChunker:
        return RequestChunker(
            lambda segments, image_urls, **kwargs: self.create_messages(
                segments,
                video_img_urls=image_urls,
                **kwargs,
            ),
            self.max_request_bytes,
            self._estimate_messages_bytes,
        )

    def _summarize_with_chunked_chat(
        self,
        source: GPTSource,
        checkpoint_key: str | None,
        source_signature: str | None,
        progress_callback: Optional[Callable[[str], None]] = None,
    ) -> str:
        chunker = self._build_chunker()

        try:
            chunks = chunker.chunk(
                source.segment,
                source.video_img_urls or [],
                title=source.title,
                tags=source.tags,
                _format=source._format,
                style=source.style,
                extras=source.extras,
            )
        except ValueError:
            chunks = chunker.chunk(
                source.segment,
                [],
                title=source.title,
                tags=source.tags,
                _format=source._format,
                style=source.style,
                extras=source.extras,
            )

        partials = []
        if checkpoint_key and source_signature:
            checkpoint = self._load_checkpoint(checkpoint_key, source_signature)
            if checkpoint and isinstance(checkpoint.get('partials'), list):
                partials = checkpoint['partials']

        if len(partials) > len(chunks):
            partials = []

        total_chunks = len(chunks)
        for chunk_index, chunk in enumerate(chunks[len(partials):], start=len(partials) + 1):
            self._emit_progress(progress_callback, f'总结中：正在处理分片 {chunk_index}/{total_chunks}')
            messages = self.create_messages(
                chunk.segments,
                title=source.title,
                tags=source.tags,
                video_img_urls=chunk.image_urls,
                _format=source._format,
                style=source.style,
                extras=source.extras,
            )
            try:
                response = self._chat_completion_create(messages)
            except Exception:
                if checkpoint_key and source_signature:
                    self._save_checkpoint(checkpoint_key, source_signature, partials, 'summarize')
                raise

            partials.append(self._extract_chat_completion_text(response))
            if checkpoint_key and source_signature:
                self._save_checkpoint(checkpoint_key, source_signature, partials, 'summarize')

        if len(partials) == 1:
            if checkpoint_key:
                self._clear_checkpoint(checkpoint_key)
            self._emit_progress(progress_callback, '总结中：响应完成')
            return partials[0]

        self._emit_progress(progress_callback, '总结中：正在合并分片结果')
        merged = self._merge_partials(partials, checkpoint_key, source_signature, progress_callback)
        if checkpoint_key:
            self._clear_checkpoint(checkpoint_key)
        self._emit_progress(progress_callback, '总结中：响应完成')
        return merged

    def summarize(
        self,
        source: GPTSource,
        progress_callback: Optional[Callable[[str], None]] = None,
    ) -> str:
        self.screenshot = source.screenshot
        self.link = source.link
        source.segment = self.ensure_segments_type(source.segment)
        checkpoint_key = source.checkpoint_key
        source_signature = self._build_source_signature(source) if checkpoint_key else None

        if hasattr(self.client, 'responses'):
            response_input = self.create_input(
                source.segment,
                title=source.title,
                tags=source.tags,
                video_img_urls=source.video_img_urls,
                _format=source._format,
                style=source.style,
                extras=source.extras,
            )

            try:
                return self._summarize_with_responses_stream(
                    response_input=response_input,
                    progress_callback=progress_callback,
                )
            except Exception:
                try:
                    return self._summarize_with_responses_create(
                        response_input=response_input,
                        progress_callback=progress_callback,
                    )
                except Exception:
                    pass

        if hasattr(self.client, 'chat'):
            return self._summarize_with_chunked_chat(
                source=source,
                checkpoint_key=checkpoint_key,
                source_signature=source_signature,
                progress_callback=progress_callback,
            )

        raise RuntimeError('当前 GPT client 不支持 responses 或 chat.completions 接口')
