def md_link(url: str, text: str | None = None, with_target_blank=False):
    if text:
        return f"[{text}](<{url}>){'{{target="_blank"}}' if with_target_blank else ''}"
    return f"<{url}>{'{{target="_blank"}}' if with_target_blank else ''}"
