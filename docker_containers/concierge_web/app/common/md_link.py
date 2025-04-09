def md_link(url: str, text: str | None = None):
    if text:
        return f'[{text}](<{url}>){{target="_blank"}}'
    return f'<{url}>{{target="_blank"}}'