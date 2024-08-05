from markdown_it import MarkdownIt
from mdit_py_plugins import attrs

md = MarkdownIt("gfm-like").use(attrs.attrs_plugin)
