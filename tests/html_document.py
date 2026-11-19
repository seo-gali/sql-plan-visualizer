"""Inspect rendered content and executable surfaces without fixing HTML layout."""

from html.parser import HTMLParser


class Document(HTMLParser):
    def __init__(self, content):
        super().__init__()
        self.source = ""
        self.text = ""
        self.ids = set()
        self.links = []
        self.scripts = []
        self.styles = []
        self.meta = {}
        self.external = []
        self.event_handlers = []
        self.in_source = False
        self.in_script = False
        self.in_style = False
        self.feed(content)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "meta":
            self.meta[attrs.get("http-equiv", attrs.get("name", "")).lower()] = (
                attrs.get("content", "")
            )
        if "id" in attrs:
            self.ids.add(attrs["id"])
        if tag == "pre" and attrs.get("id") == "sql-source":
            self.in_source = True
        if tag == "script":
            self.in_script = True
            self.scripts.append("")
        if tag == "style":
            self.in_style = True
            self.styles.append("")
        if tag == "a" and "href" in attrs:
            self.links.append(attrs["href"])
        self.event_handlers.extend(
            name for name in attrs if name.lower().startswith("on")
        )
        for name in ("src", "href"):
            if (
                attrs.get(name, "")
                .lower()
                .startswith(("http:", "https:", "//", "javascript:"))
            ):
                self.external.append(attrs[name])

    def handle_endtag(self, tag):
        if tag == "pre":
            self.in_source = False
        if tag == "script":
            self.in_script = False
        if tag == "style":
            self.in_style = False

    def handle_data(self, data):
        if self.in_source:
            self.source += data
        if self.in_script:
            self.scripts[-1] += data
        elif self.in_style:
            self.styles[-1] += data
        elif not self.in_style:
            self.text += data
