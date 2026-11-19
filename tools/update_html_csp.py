"""Refresh hashes of reviewed inline code in the repository's public HTML pages."""

import re
from base64 import b64encode
from hashlib import sha256
from html.parser import HTMLParser
from pathlib import Path


class InlineCode(HTMLParser):
    def __init__(self, content):
        super().__init__()
        self.blocks = {"script": [], "style": []}
        self.active = None
        self.feed(content)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if any(key == "style" or key.startswith("on") for key in attrs):
            raise ValueError("Use CSS classes and addEventListener before updating CSP")
        if tag == "script" and "src" in attrs:
            raise ValueError("External scripts are outside the standalone HTML policy")
        if tag in self.blocks:
            self.active = tag
            self.blocks[tag].append("")

    def handle_endtag(self, tag):
        if tag == self.active:
            self.active = None

    def handle_data(self, data):
        if self.active:
            self.blocks[self.active][-1] += data


def update(path: Path) -> None:
    content = path.read_text(encoding="utf-8")
    parsed = InlineCode(content)
    allowed = {}
    for kind, blocks in parsed.blocks.items():
        allowed[kind] = (
            " ".join(
                "'sha256-"
                + b64encode(sha256(block.encode("utf-8")).digest()).decode()
                + "'"
                for block in blocks
            )
            or "'none'"
        )
    policy = (
        f"default-src 'none'; script-src {allowed['script']}; "
        f"style-src {allowed['style']}; img-src data:; base-uri 'none'; form-action 'none'"
    )
    tags = [
        ("http-equiv", "Content-Security-Policy", policy),
        ("name", "referrer", "no-referrer"),
    ]
    for attribute, name, value in tags:
        pattern = rf'<meta\b[^>]*{attribute}=["\']{name}["\'][^>]*>'
        tag = f'<meta {attribute}="{name}" content="{value}">'
        if re.search(pattern, content, re.IGNORECASE):
            content = re.sub(pattern, tag, content, count=1, flags=re.IGNORECASE)
        else:
            content = re.sub(
                r"<head>", "<head>\n" + tag, content, count=1, flags=re.IGNORECASE
            )
    path.write_text(content, encoding="utf-8")


if __name__ == "__main__":
    for path in sorted(
        (Path(__file__).resolve().parent.parent / "docs").rglob("*.html")
    ):
        update(path)
