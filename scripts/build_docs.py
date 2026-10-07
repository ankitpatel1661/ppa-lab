"""Render the learning-track Markdown pages to PDF.

    python scripts/build_docs.py            # all pages in docs/learning_track/
    python scripts/build_docs.py day01      # pages whose file name contains "day01"

Markdown -> HTML with Python-Markdown (+ Pygments for code), then HTML -> PDF with
headless Google Chrome. The Markdown files stay the source of truth (they render
on GitHub too); the PDFs are for comfortable reading and printing.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import markdown
from pygments.formatters import HtmlFormatter

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "docs" / "learning_track"
OUT = SRC / "pdf"
CHROME_CANDIDATES = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "google-chrome",
    "chromium",
    "chromium-browser",
]

CSS = """
@page { size: A4; margin: 18mm 16mm 18mm 16mm; }
body { font-family: -apple-system, "Helvetica Neue", Arial, sans-serif; font-size: 10.5pt;
       line-height: 1.5; color: #1d1d1f; max-width: 100%; }
h1 { color: #005391; font-size: 21pt; border-bottom: 2px solid #005391; padding-bottom: 4px; }
h2 { color: #005391; font-size: 15pt; margin-top: 1.6em; border-bottom: 1px solid #d9d9d6;
     padding-bottom: 2px; page-break-after: avoid; }
h3 { color: #1d1d1f; font-size: 12pt; margin-top: 1.2em; page-break-after: avoid; }
h4 { font-size: 10.5pt; page-break-after: avoid; }
a { color: #005391; text-decoration: none; }
code { font-family: Menlo, Consolas, monospace; font-size: 8.8pt; background: #f2f4f7;
       padding: 1px 3px; border-radius: 3px; }
pre { background: #f6f8fa; border: 1px solid #e2e2de; border-radius: 4px; padding: 8px 10px;
      overflow-x: hidden; white-space: pre-wrap; word-break: break-word; page-break-inside: avoid; }
pre code { background: none; padding: 0; font-size: 8.4pt; }
table { border-collapse: collapse; width: 100%; margin: 0.6em 0 1em; font-size: 9pt;
        page-break-inside: avoid; }
th { background: #e8f0f7; text-align: left; }
th, td { border: 1px solid #d9d9d6; padding: 4px 6px; vertical-align: top; }
blockquote { border-left: 4px solid #005391; background: #f2f6fa; margin: 0.8em 0;
             padding: 6px 12px; }
blockquote p { margin: 0.3em 0; }
img { max-width: 100%; display: block; margin: 0.6em auto; page-break-inside: avoid; }
details { border: 1px solid #e2e2de; border-radius: 4px; padding: 4px 10px; margin: 0.6em 0;
          background: #fbfbfa; }
summary { font-weight: 600; }
.toc { background: #f6f8fa; border: 1px solid #e2e2de; padding: 6px 14px; border-radius: 4px; }
.toc ul { margin: 0.2em 0; }
hr { border: none; border-top: 1px solid #d9d9d6; margin: 1.5em 0; }
"""


def find_chrome() -> str:
    for candidate in CHROME_CANDIDATES:
        if Path(candidate).exists() or shutil.which(candidate):
            return candidate
    raise SystemExit("Google Chrome / Chromium not found; install it or edit CHROME_CANDIDATES.")


def to_html(md_path: Path) -> str:
    text = md_path.read_text(encoding="utf-8")
    # Answers inside <details> are collapsed on GitHub; in the PDF we want them visible.
    text = text.replace("<details>", '<details open markdown="1">')
    # GitHub task-list checkboxes -> printable ballot boxes.
    text = text.replace("- [ ] ", "- \u2610 ").replace("- [x] ", "- \u2611 ")
    body = markdown.markdown(
        text,
        extensions=["extra", "toc", "sane_lists", "codehilite", "md_in_html"],
        extension_configs={"codehilite": {"guess_lang": False, "css_class": "highlight"}},
    )
    pygments_css = HtmlFormatter(style="default").get_style_defs(".highlight")
    base = md_path.parent.as_uri() + "/"
    return (
        "<!doctype html><html><head><meta charset='utf-8'>"
        f"<base href='{base}'><title>{md_path.stem}</title>"
        f"<style>{CSS}\n{pygments_css}</style></head><body>{body}</body></html>"
    )


def render(md_path: Path, chrome: str) -> Path:
    OUT.mkdir(parents=True, exist_ok=True)
    pdf_path = OUT / f"{md_path.stem}.pdf"
    with tempfile.TemporaryDirectory() as tmp:
        html_path = Path(tmp) / f"{md_path.stem}.html"
        html_path.write_text(to_html(md_path), encoding="utf-8")
        subprocess.run(
            [chrome, "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
             "--allow-file-access-from-files", f"--print-to-pdf={pdf_path}",
             html_path.as_uri()],
            check=True, capture_output=True, timeout=120,
        )
    return pdf_path


def main(argv: list[str]) -> int:
    pattern = argv[1] if len(argv) > 1 else ""
    pages = sorted(p for p in SRC.glob("*.md") if pattern in p.name)
    if not pages:
        raise SystemExit(f"No Markdown pages in {SRC} matching {pattern!r}")
    chrome = find_chrome()
    for page in pages:
        print(f"rendered {render(page, chrome).relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
