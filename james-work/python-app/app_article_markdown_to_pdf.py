#!/Users/Shared/_AllDocMap/02_Project/gitee/james-python/.conda/bin/python

import argparse
import html
from pathlib import Path
from typing import Union

import markdown
from bs4 import BeautifulSoup
from PIL import Image
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Image as PdfImage
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer


Item = tuple[str, Union[str, Path]]


def style() -> dict[str, ParagraphStyle]:
    pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))
    css = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "title",
            parent=css["Title"],
            fontName="STSong-Light",
            fontSize=20,
            leading=26,
            spaceAfter=10,
        ),
        "h1": ParagraphStyle(
            "h1",
            parent=css["Heading1"],
            fontName="STSong-Light",
            fontSize=17,
            leading=22,
            spaceBefore=8,
            spaceAfter=6,
        ),
        "h2": ParagraphStyle(
            "h2",
            parent=css["Heading2"],
            fontName="STSong-Light",
            fontSize=15,
            leading=20,
            spaceBefore=8,
            spaceAfter=5,
        ),
        "h3": ParagraphStyle(
            "h3",
            parent=css["Heading3"],
            fontName="STSong-Light",
            fontSize=13,
            leading=18,
            spaceBefore=6,
            spaceAfter=4,
        ),
        "body": ParagraphStyle(
            "body",
            parent=css["BodyText"],
            fontName="STSong-Light",
            fontSize=11,
            leading=18,
            firstLineIndent=0,
            spaceAfter=8,
        ),
    }


def esc(text: str) -> str:
    return html.escape(text, quote=False).replace("\n", "<br/>")


def add_block(out: list[Item], node, base: Path) -> None:
    name = node.name.lower()
    if name == "p":
        text = node.get_text(" ", strip=True)
        if text:
            out.append(("body", text))
        for img in node.find_all("img"):
            out.append(("img", img_path(img.get("src", ""), base)))
        return
    if name == "img":
        out.append(("img", img_path(node.get("src", ""), base)))
        return
    if name == "ul":
        for li in node.find_all("li", recursive=False):
            text = li.get_text(" ", strip=True)
            if text:
                out.append(("body", f"• {text}"))
        return
    if name == "ol":
        for idx, li in enumerate(node.find_all("li", recursive=False), start=1):
            text = li.get_text(" ", strip=True)
            if text:
                out.append(("body", f"{idx}. {text}"))
        return
    if name == "table":
        for row in node.find_all("tr"):
            cells = [cell.get_text(" ", strip=True) for cell in row.find_all(["th", "td"])]
            if cells:
                out.append(("body", " | ".join(cells)))
        return
    if name == "blockquote":
        text = node.get_text(" ", strip=True)
        if text:
            out.append(("body", text))
        return
    if name == "pre":
        text = node.get_text("\n", strip=True)
        if text:
            out.append(("body", text))


def img_path(src: str, base: Path) -> Path:
    path = Path(src)
    if path.is_absolute():
        full = path
    else:
        full = (base / path).resolve()
    if not full.exists():
        raise FileNotFoundError(f"image not found: {src}")
    return full


def img_flow(path: Path, width: float, height: float) -> PdfImage:
    with Image.open(path) as img:
        w, h = img.size
    if w <= 0 or h <= 0:
        raise ValueError(f"invalid image size: {path}")
    rate = min(width / w, height / h, 1.0)
    return PdfImage(str(path), width=w * rate, height=h * rate)


def parse(md_path: Path) -> list[Item]:
    text = md_path.read_text(encoding="utf-8")
    body = markdown.markdown(text, extensions=["extra"])
    doc = BeautifulSoup(body, "html.parser")
    base = md_path.parent
    out: list[Item] = []
    seen = False
    for node in doc.children:
        if not getattr(node, "name", None):
            continue
        name = node.name.lower()
        if name == "h1" and not seen:
            out.append(("title", node.get_text(" ", strip=True)))
            seen = True
            continue
        if name in {"h1", "h2", "h3"}:
            out.append((name, node.get_text(" ", strip=True)))
            continue
        add_block(out, node, base)
    return out


def build(md_path: Path, pdf_path: Path) -> None:
    css = style()
    story = []
    doc = SimpleDocTemplate(
        str(pdf_path),
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
    )
    width = A4[0] - doc.leftMargin - doc.rightMargin
    height = doc.height - 12
    for kind, val in parse(md_path):
        if kind == "img":
            assert isinstance(val, Path)
            story.append(img_flow(val, width, height))
            story.append(Spacer(1, 8))
            continue
        assert isinstance(val, str)
        story.append(Paragraph(esc(str(val)), css[kind]))
        story.append(Spacer(1, 4))
    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    doc.build(story)


def args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Convert markdown article to PDF")
    p.add_argument("input", help="markdown file path")
    p.add_argument("output", nargs="?", help="optional output pdf path")
    return p.parse_args()


def main() -> int:
    arg = args()
    md_path = Path(arg.input).expanduser().resolve()
    if not md_path.exists():
        raise FileNotFoundError(f"markdown not found: {md_path}")
    pdf_path = Path(arg.output).expanduser().resolve() if arg.output else md_path.with_suffix(".pdf")
    build(md_path, pdf_path)
    print(str(pdf_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
