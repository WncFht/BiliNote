import re


def prepend_source_link(markdown: str | None, source_url: str) -> str | None:
    """
    在笔记开头添加来源链接；若首个非空行已包含来源链接，则更新该行并避免重复。
    """
    if markdown is None:
        return None

    source = (source_url or '').strip()
    if not source:
        return markdown

    header = f'> 来源链接：{source}'
    lines = markdown.splitlines()
    first_non_empty_idx = None
    for idx, line in enumerate(lines):
        if line.strip():
            first_non_empty_idx = idx
            break

    if first_non_empty_idx is not None:
        first_line = lines[first_non_empty_idx].strip()
        if first_line.startswith('> 来源链接：') or first_line.startswith('来源链接：'):
            lines[first_non_empty_idx] = header
            return '\n'.join(lines)

    if markdown.strip():
        return f'{header}\n\n{markdown}'
    return header


def normalize_math_delimiters(markdown: str) -> str:
    """
    将 LaTeX 的括号分隔符统一转换为 Markdown 更友好的美元分隔符。
    """

    def replace_block(match: re.Match[str]) -> str:
        content = match.group(1).strip()
        return f'$$\n{content}\n$$'

    def replace_inline(match: re.Match[str]) -> str:
        content = match.group(1).strip()
        return f'${content}$'

    normalized = re.sub(r'\\\[\s*([\s\S]*?)\s*\\\]', replace_block, markdown)
    normalized = re.sub(r'\\\((.+?)\\\)', replace_inline, normalized)
    return normalized


def replace_content_markers(markdown: str, video_id: str, platform: str = 'bilibili') -> str:
    """
    替换 *Content-04:16*、Content-04:16 或 Content-[04:16] 为超链接，跳转到对应平台视频的时间位置
    """
    pattern = r'(?:\*?)Content-(?:\[(\d{2}):(\d{2})\]|(\d{2}):(\d{2}))'
    safe_video_id = video_id

    def replacer(match):
        mm = match.group(1) or match.group(3)
        ss = match.group(2) or match.group(4)
        total_seconds = int(mm) * 60 + int(ss)

        if platform == 'bilibili':
            parsed_video_id = safe_video_id.replace('_p', '?p=')
            url = f'https://www.bilibili.com/video/{parsed_video_id}&t={total_seconds}'
        elif platform == 'youtube':
            url = f'https://www.youtube.com/watch?v={safe_video_id}&t={total_seconds}s'
        elif platform == 'douyin':
            url = f'https://www.douyin.com/video/{safe_video_id}'
            return f'[原片 @ {mm}:{ss}]({url})'
        else:
            return f'({mm}:{ss})'

        return f'[原片 @ {mm}:{ss}]({url})'

    return re.sub(pattern, replacer, markdown)
