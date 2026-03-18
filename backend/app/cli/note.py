from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime
import json
import re
from threading import Lock
import time
import uuid
from pathlib import Path
from typing import Callable, Optional

import typer

from app.runtime_config import initialize_backend_runtime
from app.validators.video_url_validator import is_supported_video_url


DEFAULT_PROVIDER_ID = "openai"
DEFAULT_MODEL_NAME = "gpt-5.4"
DEFAULT_STYLE = "detailed"
DEFAULT_VIDEO_INTERVAL = 4
DEFAULT_GRID_SIZE = [3, 3]
DEFAULT_PLATFORM = "bilibili"
DEFAULT_MARKDOWN_OUTPUT_DIR = Path("/Users/fanghaotian/Desktop/obsidian/视频")

app = typer.Typer(help="Generate BiliNote markdown notes from one or more video URLs.")

_RUNTIME_INITIALIZED = False
_RUNTIME_INITIALIZATION_LOCK = Lock()
INVALID_FILENAME_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
WHITESPACE_RE = re.compile(r"\s+")
GENERIC_H1_TITLES = {"目录", "toc", "contents", "tableofcontents"}


@dataclass
class NoteGenerationOutput:
    output_path: Path
    video_id: str | None = None
    title: str | None = None


@dataclass
class BatchGenerationSummary:
    output_paths: list[Path]
    failures: list[str]
    items: list[dict[str, object]]


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def initialize_runtime() -> None:
    global _RUNTIME_INITIALIZED

    if _RUNTIME_INITIALIZED:
        return

    with _RUNTIME_INITIALIZATION_LOCK:
        if _RUNTIME_INITIALIZED:
            return

        backend_root = project_root()
        initialize_backend_runtime(backend_root / ".env")
        _RUNTIME_INITIALIZED = True


def detect_platform(video_url: str) -> str:
    if video_url.startswith(("http://", "https://")):
        if "bilibili.com" in video_url or "b23.tv" in video_url:
            return "bilibili"
        if "youtube.com" in video_url or "youtu.be" in video_url:
            return "youtube"
        if "douyin.com" in video_url:
            return "douyin"
        if "kuaishou.com" in video_url:
            return "kuaishou"
    elif Path(video_url).exists():
        return "local"

    raise typer.BadParameter("Unsupported video URL or local file path.")


def build_formats(screenshot: bool) -> list[str]:
    formats = ["toc", "summary"]
    if screenshot:
        formats.append("screenshot")
    return formats


def build_video_options(screenshot: bool) -> tuple[bool, list[int]]:
    if screenshot:
        return True, DEFAULT_GRID_SIZE.copy()
    return False, []


def note_generator_class():
    from app.services.note import NoteGenerator

    return NoteGenerator


def medium_quality():
    from app.enmus.note_enums import DownloadQuality

    return DownloadQuality.medium


def extract_h1_title(markdown: str) -> str | None:
    for line in markdown.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if not stripped.startswith("# "):
            continue
        title = stripped[2:].strip().strip("#").strip()
        return title or None
    return None


def sanitize_filename(title: str) -> str:
    sanitized = INVALID_FILENAME_CHARS.sub(" ", title)
    sanitized = WHITESPACE_RE.sub(" ", sanitized).strip(" .")
    return sanitized


def normalize_title_key(title: str) -> str:
    return re.sub(r"[\s\-_:/|]+", "", title).lower()


def is_generic_h1_title(title: str | None) -> bool:
    if not title:
        return False
    return normalize_title_key(title) in GENERIC_H1_TITLES


def resolve_output_path(
    markdown: str,
    output: Optional[Path],
    fallback_stem: str,
    preferred_stem: str | None = None,
    unique_prefix: str | None = None,
) -> Path:
    if output is None:
        output_dir = DEFAULT_MARKDOWN_OUTPUT_DIR
    elif output.suffix.lower() == ".md":
        output_dir = output.parent
    else:
        output_dir = output

    title = extract_h1_title(markdown)
    if title and not is_generic_h1_title(title):
        filename_stem = sanitize_filename(title)
    else:
        filename_stem = (
            sanitize_filename(preferred_stem or "")
            or sanitize_filename(fallback_stem)
            or "note"
        )

    if unique_prefix:
        safe_prefix = sanitize_filename(unique_prefix)
        if safe_prefix and filename_stem != safe_prefix and not filename_stem.startswith(f"{safe_prefix} "):
            filename_stem = f"{safe_prefix} {filename_stem}" if filename_stem else safe_prefix

    return output_dir / f"{filename_stem}.md"


def write_markdown(markdown: str, output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(markdown, encoding="utf-8")
    return output_path


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def append_progress_event(progress_jsonl: Optional[Path], event: dict[str, object]) -> None:
    if progress_jsonl is None:
        return
    progress_jsonl.parent.mkdir(parents=True, exist_ok=True)
    with progress_jsonl.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=False) + "\n")


def write_manifest(
    manifest_json: Optional[Path],
    *,
    started_at: str,
    finished_at: str,
    jobs: int,
    items: list[dict[str, object]],
) -> None:
    if manifest_json is None:
        return
    manifest_json.parent.mkdir(parents=True, exist_ok=True)
    manifest = {
        "started_at": started_at,
        "finished_at": finished_at,
        "jobs": jobs,
        "total": len(items),
        "success_count": sum(item["status"] == "success" for item in items),
        "failure_count": sum(item["status"] == "failed" for item in items),
        "items": items,
    }
    manifest_json.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")


def build_batch_item(
    *,
    index: int,
    video_url: str,
    status: str,
    output_path: Path | None = None,
    video_id: str | None = None,
    title: str | None = None,
    error: str | None = None,
    duration_seconds: float | None = None,
) -> dict[str, object]:
    return {
        "index": index,
        "video_url": video_url,
        "status": status,
        "output_path": str(output_path) if output_path is not None else None,
        "video_id": video_id,
        "title": title,
        "duration_seconds": duration_seconds,
        "error": error,
    }


def normalize_generation_output(result: Path | NoteGenerationOutput) -> NoteGenerationOutput:
    if isinstance(result, NoteGenerationOutput):
        return result
    return NoteGenerationOutput(output_path=result)


def format_generation_error(exc: BaseException) -> str:
    if isinstance(exc, typer.Exit):
        exit_code = getattr(exc, "exit_code", None)
        return f"exit code {exit_code}" if exit_code is not None else "exit"
    return str(exc) or exc.__class__.__name__


def validate_video_url(video_url: str) -> None:
    if not is_supported_video_url(video_url) and not Path(video_url).exists():
        raise typer.BadParameter("Unsupported video URL or local file path.")


def validate_output_path_option(output: Optional[Path], video_count: int) -> Optional[Path]:
    if video_count > 1 and output is not None and output.suffix.lower() == ".md":
        raise typer.BadParameter("Batch mode requires --output to be a directory, not a .md file.")
    return output


def generate_note(
    video_url: str,
    style: str,
    screenshot: bool,
    output: Optional[Path],
    batch_mode: bool = False,
    progress_callback: Optional[Callable[[str, Optional[str]], None]] = None,
) -> NoteGenerationOutput:
    validate_video_url(video_url)

    initialize_runtime()

    task_id = str(uuid.uuid4())
    platform = detect_platform(video_url)
    video_understanding, grid_size = build_video_options(screenshot)

    result = note_generator_class()().generate(
        video_url=video_url,
        platform=platform,
        quality=medium_quality(),
        task_id=task_id,
        model_name=DEFAULT_MODEL_NAME,
        provider_id=DEFAULT_PROVIDER_ID,
        link=False,
        screenshot=screenshot,
        _format=build_formats(screenshot),
        style=style,
        extras=None,
        video_understanding=video_understanding,
        video_interval=DEFAULT_VIDEO_INTERVAL,
        grid_size=grid_size,
        progress_callback=progress_callback,
    )

    if result is None:
        raise typer.Exit(code=1)

    fallback_stem = result.audio_meta.video_id or task_id
    output_path = resolve_output_path(
        markdown=result.markdown,
        output=output,
        fallback_stem=fallback_stem,
        preferred_stem=result.audio_meta.title,
        unique_prefix=result.audio_meta.video_id if batch_mode else None,
    )
    written_path = write_markdown(result.markdown, output_path)
    return NoteGenerationOutput(
        output_path=written_path,
        video_id=result.audio_meta.video_id,
        title=result.audio_meta.title,
    )


def generate_notes(
    video_urls: list[str],
    style: str,
    screenshot: bool,
    output: Optional[Path],
    jobs: int,
    manifest_json: Optional[Path] = None,
    progress_jsonl: Optional[Path] = None,
    continue_on_error: bool = False,
) -> BatchGenerationSummary:
    del continue_on_error  # batch mode always records all results before returning

    if not video_urls:
        raise typer.BadParameter("At least one video URL or local file path is required.")

    for video_url in video_urls:
        validate_video_url(video_url)

    output = validate_output_path_option(output, len(video_urls))

    started_at = now_iso()
    worker_count = min(max(jobs, 1), len(video_urls))
    append_progress_event(
        progress_jsonl,
        {
            "event": "batch_started",
            "total": len(video_urls),
            "jobs": worker_count,
            "ts": started_at,
        },
    )

    items: list[dict[str, object] | None] = [None] * len(video_urls)
    output_paths_by_index: list[Path | None] = [None] * len(video_urls)
    failures: list[str] = []

    def emit_note_progress(index: int, video_url: str) -> Callable[[str, Optional[str]], None]:
        def callback(status: str, message: Optional[str] = None) -> None:
            append_progress_event(
                progress_jsonl,
                {
                    "event": "note_progress",
                    "index": index,
                    "video_url": video_url,
                    "status": status,
                    "message": message,
                    "ts": now_iso(),
                },
            )

        return callback

    if len(video_urls) == 1:
        video_url = video_urls[0]
        append_progress_event(
            progress_jsonl,
            {"event": "note_started", "index": 0, "video_url": video_url, "ts": now_iso()},
        )
        started = time.monotonic()
        try:
            normalized = normalize_generation_output(
                generate_note(
                    video_url,
                    style=style,
                    screenshot=screenshot,
                    output=output,
                    batch_mode=False,
                    progress_callback=emit_note_progress(0, video_url),
                )
            )
            duration_seconds = round(time.monotonic() - started, 3)
            output_paths_by_index[0] = normalized.output_path
            items[0] = build_batch_item(
                index=0,
                video_url=video_url,
                status="success",
                output_path=normalized.output_path,
                video_id=normalized.video_id,
                title=normalized.title,
                duration_seconds=duration_seconds,
            )
            append_progress_event(
                progress_jsonl,
                {
                    "event": "note_succeeded",
                    "index": 0,
                    "video_url": video_url,
                    "output_path": str(normalized.output_path),
                    "duration_seconds": duration_seconds,
                    "ts": now_iso(),
                },
            )
        except Exception as exc:
            error_message = format_generation_error(exc)
            duration_seconds = round(time.monotonic() - started, 3)
            failures.append(f"{video_url}: {error_message}")
            items[0] = build_batch_item(
                index=0,
                video_url=video_url,
                status="failed",
                error=error_message,
                duration_seconds=duration_seconds,
            )
            append_progress_event(
                progress_jsonl,
                {
                    "event": "note_failed",
                    "index": 0,
                    "video_url": video_url,
                    "error": error_message,
                    "ts": now_iso(),
                },
            )
    else:
        initialize_runtime()
        future_to_context: dict[object, tuple[int, str, float]] = {}

        def run_note_job(index: int, video_url: str) -> NoteGenerationOutput:
            append_progress_event(
                progress_jsonl,
                {"event": "note_started", "index": index, "video_url": video_url, "ts": now_iso()},
            )
            return normalize_generation_output(
                generate_note(
                    video_url,
                    style,
                    screenshot,
                    output,
                    True,
                    progress_callback=emit_note_progress(index, video_url),
                )
            )

        with ThreadPoolExecutor(max_workers=worker_count) as executor:
            for index, video_url in enumerate(video_urls):
                future = executor.submit(run_note_job, index, video_url)
                future_to_context[future] = (index, video_url, time.monotonic())

            for future in as_completed(future_to_context):
                index, video_url, started = future_to_context[future]
                duration_seconds = round(time.monotonic() - started, 3)
                try:
                    normalized = future.result()
                    output_paths_by_index[index] = normalized.output_path
                    items[index] = build_batch_item(
                        index=index,
                        video_url=video_url,
                        status="success",
                        output_path=normalized.output_path,
                        video_id=normalized.video_id,
                        title=normalized.title,
                        duration_seconds=duration_seconds,
                    )
                    append_progress_event(
                        progress_jsonl,
                        {
                            "event": "note_succeeded",
                            "index": index,
                            "video_url": video_url,
                            "output_path": str(normalized.output_path),
                            "duration_seconds": duration_seconds,
                            "ts": now_iso(),
                        },
                    )
                except Exception as exc:
                    error_message = format_generation_error(exc)
                    failures.append(f"{video_url}: {error_message}")
                    items[index] = build_batch_item(
                        index=index,
                        video_url=video_url,
                        status="failed",
                        error=error_message,
                        duration_seconds=duration_seconds,
                    )
                    append_progress_event(
                        progress_jsonl,
                        {
                            "event": "note_failed",
                            "index": index,
                            "video_url": video_url,
                            "error": error_message,
                            "ts": now_iso(),
                        },
                    )

    completed_items = [item for item in items if item is not None]
    finished_at = now_iso()
    append_progress_event(
        progress_jsonl,
        {
            "event": "batch_finished",
            "success_count": sum(item["status"] == "success" for item in completed_items),
            "failure_count": sum(item["status"] == "failed" for item in completed_items),
            "ts": finished_at,
        },
    )
    write_manifest(
        manifest_json,
        started_at=started_at,
        finished_at=finished_at,
        jobs=worker_count,
        items=completed_items,
    )

    return BatchGenerationSummary(
        output_paths=[path for path in output_paths_by_index if path is not None],
        failures=failures,
        items=completed_items,
    )


@app.command()
def main(
    video_urls: list[str] = typer.Argument(..., help="One or more video URLs to summarize."),
    style: str = typer.Option(DEFAULT_STYLE, "--style", help="Note style."),
    screenshot: bool = typer.Option(False, "--screenshot/--no-screenshot", help="Include screenshots in markdown."),
    output: Optional[Path] = typer.Option(
        None,
        "--output",
        help="Optional output directory or path hint. Final filename comes from the markdown H1 title.",
    ),
    jobs: int = typer.Option(
        1,
        "--jobs",
        min=1,
        help="Number of concurrent jobs when multiple URLs are provided.",
    ),
    manifest_json: Optional[Path] = typer.Option(
        None,
        "--manifest-json",
        help="Optional JSON file describing per-URL batch results.",
    ),
    progress_jsonl: Optional[Path] = typer.Option(
        None,
        "--progress-jsonl",
        help="Optional JSONL file for streaming batch progress events.",
    ),
    continue_on_error: bool = typer.Option(
        False,
        "--continue-on-error",
        help="Continue processing remaining URLs after individual failures and record partial results.",
    ),
) -> None:
    try:
        summary = generate_notes(
            video_urls=video_urls,
            style=style,
            screenshot=screenshot,
            output=output,
            jobs=jobs,
            manifest_json=manifest_json,
            progress_jsonl=progress_jsonl,
            continue_on_error=continue_on_error,
        )
    except typer.BadParameter as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=2) from exc
    except typer.Exit:
        raise
    except Exception as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1) from exc

    for output_path in summary.output_paths:
        typer.echo(str(output_path))

    if summary.failures:
        joined_failures = "\n".join(summary.failures)
        typer.echo(f"Error: Failed to generate one or more notes:\n{joined_failures}", err=True)
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
