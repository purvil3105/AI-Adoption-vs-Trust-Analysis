"""Render reports/insight_memo.md to a self-contained HTML page and a PDF (via headless Edge/Chrome, free).

Usage:  python -m src.memo
"""
import base64
import re
import shutil
import subprocess
from pathlib import Path

import markdown

from src.config import ROOT

REPORTS = ROOT / "reports"
BROWSERS = [r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
            r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            "msedge", "google-chrome", "chromium", "chrome"]

CSS = """
@page { size: A4; margin: 16mm 15mm; }
body { font-family: "Segoe UI", system-ui, -apple-system, sans-serif; color: #0b0b0b; background: #fcfcfb;
       max-width: 820px; margin: 24px auto; padding: 0 16px; font-size: 13.5px; line-height: 1.5; }
h1 { font-size: 22px; margin-bottom: 2px; } h2 { font-size: 16px; margin-top: 22px; border-bottom: 1px solid #e1e0d9; padding-bottom: 3px; }
h3 { font-size: 14px; margin-bottom: 4px; }
p, li { color: #23231f; } em { color: #52514e; }
img { max-width: 100%; border: 1px solid #e1e0d9; border-radius: 8px; margin: 6px 0; }
table { border-collapse: collapse; width: 100%; font-size: 12px; font-variant-numeric: tabular-nums; }
th, td { border-bottom: 1px solid #e1e0d9; padding: 4px 6px; text-align: left; }
th { color: #52514e; }
blockquote { margin: 8px 0; padding: 6px 12px; border-left: 3px solid #2a78d6; background: #f3f6fb; }
code { font-size: 12px; background: #f0efec; padding: 0 3px; border-radius: 3px; }
@media print { body { margin: 0; max-width: none; } h2 { break-after: avoid; } img, table { break-inside: avoid; } }
"""


def inline_images(html: str, base: Path) -> str:
    def repl(m):
        src = m.group(1)
        p = (base / src).resolve()
        if p.exists():
            data = base64.b64encode(p.read_bytes()).decode()
            return f'src="data:image/png;base64,{data}"'
        return m.group(0)
    return re.sub(r'src="([^"]+\.png)"', repl, html)


def find_browser() -> str | None:
    for b in BROWSERS:
        if Path(b).exists() or shutil.which(b):
            return b
    return None


def main() -> None:
    md_path = REPORTS / "insight_memo.md"
    body = markdown.markdown(md_path.read_text(encoding="utf-8"), extensions=["tables", "sane_lists"])
    html = (f'<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" '
            f'content="width=device-width, initial-scale=1"><title>AI Trust Insight Memo</title><style>{CSS}</style>'
            f"</head><body>{inline_images(body, md_path.parent)}</body></html>")
    out_html = REPORTS / "insight_memo.html"
    out_html.write_text(html, encoding="utf-8")
    print(f"wrote {out_html}")
    browser = find_browser()
    if not browser:
        print("no Edge/Chrome found - skipping PDF (open the HTML and print to PDF instead)")
        return
    out_pdf = REPORTS / "insight_memo.pdf"
    before = out_pdf.stat().st_mtime if out_pdf.exists() else None
    try:
        subprocess.run([browser, "--headless", "--disable-gpu", "--no-pdf-header-footer",
                        f"--print-to-pdf={out_pdf}", out_html.as_uri()], check=False, timeout=120,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except (OSError, subprocess.TimeoutExpired) as e:   # a missing/hung browser must not fail the pipeline
        print(f"PDF export skipped ({type(e).__name__}) - open the HTML and print to PDF")
        return
    updated = out_pdf.exists() and out_pdf.stat().st_mtime != before
    print(f"wrote {out_pdf}" if updated else "PDF export failed - open the HTML and print to PDF")


if __name__ == "__main__":
    main()
