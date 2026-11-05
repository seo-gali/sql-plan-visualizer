"""Phase 0 only: inspect identifier positions and draw reference connections."""

import argparse
import html
from pathlib import Path

import sqlglot
from sqlglot import exp


def render_probe(sql: str) -> str:
    ast = sqlglot.parse_one(sql, read="postgres")
    identifiers = sorted(
        {
            (node.this.meta["start"], node.this.meta["end"] + 1)
            for node in ast.walk()
            if isinstance(node, (exp.Table, exp.Column))
            and isinstance(node.this, exp.Identifier)
            and "start" in node.this.meta
        }
    )
    fragments = []
    references = []
    cursor = 0
    for index, (start, end) in enumerate(identifiers):
        label = html.escape(sql[start:end])
        fragments.append(html.escape(sql[cursor:start]))
        fragments.append(
            f'<span id="source-{index}" data-link="{index}" tabindex="0">{label}</span>'
        )
        references.append(
            f'<li><a id="reference-{index}" data-link="{index}" '
            f'href="#source-{index}">{label}</a></li>'
        )
        cursor = end
    fragments.append(html.escape(sql[cursor:]))
    return (
        '<!doctype html><html lang="en"><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        "<title>SQLPVI Phase 0 probe</title>"
        "<style>body{font:16px system-ui;margin:24px}"
        "main{position:relative;display:flex;gap:100px;align-items:start}"
        "pre{white-space:pre-wrap;margin:0;max-width:65%}"
        "svg{position:absolute;inset:0;pointer-events:none;overflow:visible}"
        ".active{background:#fde68a}a{color:#164a8a}</style>"
        "<h1>SQLPVI Phase 0 probe</h1><p>PARSED · STATIC · Identifier mapping</p>"
        '<main><pre aria-label="SQL source">'
        + "".join(fragments)
        + '</pre><ul aria-label="References">'
        + "".join(references)
        + '</ul><svg aria-hidden="true"></svg></main>'
        "<script>const main=document.querySelector('main');"
        "const svg=document.querySelector('svg');"
        "function draw(){svg.replaceChildren();"
        "const origin=main.getBoundingClientRect();"
        "for(const ref of document.querySelectorAll('[id^=reference-]')){"
        "const target=document.getElementById('source-'+ref.dataset.link);"
        "const a=ref.getBoundingClientRect(),b=target.getBoundingClientRect();"
        "const line=document.createElementNS('http://www.w3.org/2000/svg','line');"
        "for(const [key,value] of Object.entries({x1:a.left-origin.left,"
        "y1:a.top+a.height/2-origin.top,x2:b.right-origin.left,"
        "y2:b.top+b.height/2-origin.top,stroke:'#64748b'}))"
        "line.setAttribute(key,String(value));svg.append(line);}}"
        "function highlight(event){const target=event.target.closest('[data-link]');"
        "for(const node of document.querySelectorAll('[data-link]'))"
        "node.classList.toggle('active',Boolean(target)&&"
        "node.dataset.link===target.dataset.link);}"
        "main.addEventListener('mouseover',highlight);"
        "main.addEventListener('focusin',highlight);"
        "main.addEventListener('mouseleave',()=>highlight({target:main}));"
        "main.addEventListener('focusout',()=>highlight({target:main}));"
        "window.addEventListener('resize',draw);draw();</script></html>"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("sql", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        render_probe(args.sql.read_text(encoding="utf-8")), encoding="utf-8"
    )
    print(args.output)
