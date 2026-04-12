import subprocess
import sys
from pathlib import Path

import pdfplumber
from PIL import Image


ROOT = Path(__file__).resolve().parents[3]
FILE = ROOT / "james-work/python-app/app_article_markdown_to_pdf.py"


def test_cli_generates_pdf_with_text_and_local_image(tmp_path):
    img_dir = tmp_path / "images"
    img_dir.mkdir()
    img = img_dir / "sample.png"
    Image.new("RGB", (120, 80), color=(220, 30, 30)).save(img)

    md = tmp_path / "article.md"
    md.write_text(
        "# 示例标题\n\n第一段正文。\n\n![](images/sample.png)\n\n第二段正文。\n",
        encoding="utf-8",
    )

    out = tmp_path / "article.pdf"
    res = subprocess.run(
        [sys.executable, str(FILE), str(md)],
        capture_output=True,
        text=True,
        cwd=str(ROOT),
    )

    assert res.returncode == 0, res.stderr or res.stdout
    assert out.exists()
    assert out.stat().st_size > 0

    with pdfplumber.open(str(out)) as doc:
        text = "\n".join(page.extract_text() or "" for page in doc.pages)
        assert "示例标题" in text
        assert "第一段正文" in text
        assert "第二段正文" in text
        assert sum(len(page.images) for page in doc.pages) >= 1


def test_cli_scales_tall_image_to_fit_page(tmp_path):
    img_dir = tmp_path / "images"
    img_dir.mkdir()
    img = img_dir / "tall.png"
    Image.new("RGB", (600, 2200), color=(30, 90, 220)).save(img)

    md = tmp_path / "article.md"
    md.write_text(
        "# 高图文章\n\n![](images/tall.png)\n\n尾段。\n",
        encoding="utf-8",
    )

    res = subprocess.run(
        [sys.executable, str(FILE), str(md)],
        capture_output=True,
        text=True,
        cwd=str(ROOT),
    )

    assert res.returncode == 0, res.stderr or res.stdout
    assert (tmp_path / "article.pdf").exists()


def test_cli_preserves_table_and_list_content(tmp_path):
    md = tmp_path / "article.md"
    md.write_text(
        "## 指标体系内容介绍\n\n"
        "| 字段 | 说明 |\n"
        "| --- | --- |\n"
        "| launch | 启动 |\n\n"
        "1. **基础指标**：包含启动数\n"
        "2. **派生指标**：包含DAU\n",
        encoding="utf-8",
    )

    out = tmp_path / "article.pdf"
    res = subprocess.run(
        [sys.executable, str(FILE), str(md)],
        capture_output=True,
        text=True,
        cwd=str(ROOT),
    )

    assert res.returncode == 0, res.stderr or res.stdout
    with pdfplumber.open(str(out)) as doc:
        text = "\n".join(page.extract_text() or "" for page in doc.pages)
        assert "launch" in text
        assert "启动" in text
        assert "基础指标" in text
        assert "派生指标" in text
