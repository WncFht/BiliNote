from __future__ import annotations

import uuid
from pathlib import Path
from typing import Optional

import typer

from app.runtime_config import initialize_backend_runtime
from app.validators.video_url_validator import is_supported_video_url


DEFAULT_PROVIDER_ID = "openai"
DEFAULT_MODEL_NAME = "gpt-5.4"
DEFAULT_STYLE = "detailed"
DEFAULT_VIDEO_INTERVAL = 4
DEFAULT_GRID_SIZE = [3, 3]
DEFAULT_PLATFORM = "bilibili"

app = typer.Typer(help="Generate BiliNote markdown notes from a video URL.")

_RUNTIME_INITIALIZED = False


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def initialize_runtime() -> None:
    global _RUNTIME_INITIALIZED

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


def default_output_path(task_id: str) -> Path:
    return note_output_dir() / f"{task_id}.md"


def note_output_dir() -> Path:
    from app.services.note import NOTE_OUTPUT_DIR

    return NOTE_OUTPUT_DIR


def note_generator_class():
    from app.services.note import NoteGenerator

    return NoteGenerator


def medium_quality():
    from app.enmus.note_enums import DownloadQuality

    return DownloadQuality.medium


def write_markdown(markdown: str, output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(markdown, encoding="utf-8")
    return output_path


def generate_note(
    video_url: str,
    style: str,
    screenshot: bool,
    output: Optional[Path],
) -> Path:
    if not is_supported_video_url(video_url) and not Path(video_url).exists():
        raise typer.BadParameter("Unsupported video URL or local file path.")

    initialize_runtime()

    task_id = str(uuid.uuid4())
    platform = detect_platform(video_url)

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
        video_understanding=True,
        video_interval=DEFAULT_VIDEO_INTERVAL,
        grid_size=DEFAULT_GRID_SIZE.copy(),
    )

    if result is None:
        raise typer.Exit(code=1)

    output_path = output or default_output_path(task_id)
    return write_markdown(result.markdown, output_path)


@app.command()
def main(
    video_url: str = typer.Argument(..., help="Video URL to summarize."),
    style: str = typer.Option(DEFAULT_STYLE, "--style", help="Note style."),
    screenshot: bool = typer.Option(True, "--screenshot/--no-screenshot", help="Include screenshots in markdown."),
    output: Optional[Path] = typer.Option(None, "--output", help="Optional markdown output path."),
) -> None:
    try:
        output_path = generate_note(
            video_url=video_url,
            style=style,
            screenshot=screenshot,
            output=output,
        )
    except typer.BadParameter as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=2) from exc
    except typer.Exit:
        raise
    except Exception as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1) from exc

    typer.echo(str(output_path))


if __name__ == "__main__":
    app()
