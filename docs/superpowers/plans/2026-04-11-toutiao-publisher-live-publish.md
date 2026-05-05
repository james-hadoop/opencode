# Toutiao Publisher Live Publish Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `james-work/python-app/app_toutiao_ariticle_publisher.py` complete a real Toutiao article publish flow, where a successfully verified draft is also treated as success.

**Architecture:** Keep the current single-file Playwright publisher intact, but extract small testable helpers for cover selection and file-input uploads so the fragile browser flow is fixed with narrow, regression-driven changes. Use unit tests for deterministic logic and fake Playwright objects, then finish with one real browser run using the specified Conda Python interpreter and QR login.

**Tech Stack:** Python 3, pytest, Playwright sync API, pathlib, tempfile/tmp_path, monkeypatch

---

### Task 1: Fix the undefined `local_images` publish path with a regression test

**Files:**

- Create: `james-work/python-app/tests/test_app_toutiao_ariticle_publisher.py`
- Modify: `james-work/python-app/app_toutiao_ariticle_publisher.py:1242-1305`
- Test: `james-work/python-app/tests/test_app_toutiao_ariticle_publisher.py`

- [ ] **Step 1: Write the failing regression test for cover selection inside `publish_article`**

```python
import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
FILE = ROOT / "james-work/python-app/app_toutiao_ariticle_publisher.py"
SPEC = importlib.util.spec_from_file_location("toutiao_publisher", FILE)
mod = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(mod)


class FakeBtn:
    def __init__(self):
        self.clicked = False

    def is_visible(self, timeout=None):
        return True

    def click(self, timeout=None):
        self.clicked = True

    def bounding_box(self):
        return {"width": 120, "height": 32}


class FakeLocator:
    def __init__(self):
        self.btn = FakeBtn()

    @property
    def first(self):
        return self.btn

    def count(self):
        return 1

    def nth(self, idx):
        return self.btn


class FakePage:
    def goto(self, *args, **kwargs):
        return None

    def wait_for_timeout(self, *args, **kwargs):
        return None

    def evaluate(self, *args, **kwargs):
        return None

    def locator(self, *args, **kwargs):
        return FakeLocator()

    def inner_text(self, *args, **kwargs):
        return "发布成功"


def test_publish_article_uses_first_three_images_for_cover(tmp_path, monkeypatch):
    paths = []
    for idx in range(4):
        path = tmp_path / f"img-{idx}.png"
        path.write_bytes(b"img")
        paths.append(str(path))

    pub = mod.ToutiaoPublisher(headless=True)
    pub.page = FakePage()

    seen = {}
    monkeypatch.setattr(pub, "_close_popups", lambda: None)
    monkeypatch.setattr(pub, "_close_ai_assistant", lambda: None)
    monkeypatch.setattr(pub, "_find_and_fill_title", lambda title: True)
    monkeypatch.setattr(pub, "_fill_editor", lambda body: True)
    monkeypatch.setattr(pub, "_insert_images_to_editor", lambda images: len(images))
    monkeypatch.setattr(pub, "_select_ad_revenue", lambda: True)
    monkeypatch.setattr(pub, "_wait_for_publish_complete", lambda: True)
    monkeypatch.setattr(pub, "_verify_article_on_manage_page", lambda title: True)
    monkeypatch.setattr(pub, "_take_debug_screenshot", lambda name: None)

    def capture(images):
        seen["images"] = images
        return True

    monkeypatch.setattr(pub, "_upload_cover_image", capture)

    ok, msg, url = pub.publish_article("标题", "正文", paths, None)

    assert ok is True
    assert msg == "发布成功"
    assert seen["images"] == paths[:3]
```

- [ ] **Step 2: Run the regression test and verify it fails with `NameError: name 'local_images' is not defined`**

Run: `"/Users/Shared/_AllDocMap/02_Project/gitee/james-python/.conda/bin/python" -m pytest james-work/python-app/tests/test_app_toutiao_ariticle_publisher.py::test_publish_article_uses_first_three_images_for_cover -v`

Expected: FAIL with a traceback from `publish_article()` at the `if local_images and len(local_images) >= 3:` branch.

- [ ] **Step 3: Write the minimal implementation by extracting a cover-picker helper and using it inside `publish_article`**

```python
def pick_cover(images: List[str] | None, cover: str | None) -> List[str]:
    paths = [path for path in (images or []) if path and os.path.exists(path)]
    if len(paths) >= 3:
        return paths[:3]
    if cover and os.path.exists(cover):
        return [cover]
    return []


def publish_article(self, title: str, content: str, images: List[str] = None, cover_image: str = None) -> Tuple[bool, str, str]:
    ...
    covers = pick_cover(images, cover_image)
    if len(covers) >= 3:
        if self._upload_cover_image(covers):
            print(f"  ✓ 封面图已上传 ({len(covers)} 张)")
        else:
            print("  ⚠ 封面图上传失败")
    elif len(covers) == 1:
        if self._upload_cover_image(covers[0]):
            print("  ✓ 封面图已上传")
        else:
            print("  ⚠ 封面图上传失败")
    else:
        print("  ⚠ 无封面图，跳过")
```

- [ ] **Step 4: Re-run the regression test and verify it passes**

Run: `"/Users/Shared/_AllDocMap/02_Project/gitee/james-python/.conda/bin/python" -m pytest james-work/python-app/tests/test_app_toutiao_ariticle_publisher.py::test_publish_article_uses_first_three_images_for_cover -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add james-work/python-app/app_toutiao_ariticle_publisher.py james-work/python-app/tests/test_app_toutiao_ariticle_publisher.py
git commit -m "fix: restore cover selection in toutiao publisher"
```

### Task 2: Make hidden file inputs uploadable for body images and cover images

**Files:**

- Modify: `james-work/python-app/app_toutiao_ariticle_publisher.py:780-825`
- Modify: `james-work/python-app/app_toutiao_ariticle_publisher.py:942-1006`
- Modify: `james-work/python-app/tests/test_app_toutiao_ariticle_publisher.py`
- Test: `james-work/python-app/tests/test_app_toutiao_ariticle_publisher.py`

- [ ] **Step 1: Write the failing tests that show hidden file inputs must still receive `set_input_files()`**

```python
class FakeInput:
    def __init__(self, visible=False):
        self.visible = visible
        self.files = None

    def is_visible(self, timeout=None):
        return self.visible

    def set_input_files(self, files):
        self.files = files


class FakeInputs:
    def __init__(self, items):
        self.items = items

    def count(self):
        return len(self.items)

    def nth(self, idx):
        return self.items[idx]


def test_set_files_uses_hidden_file_inputs():
    hidden = FakeInput(visible=False)
    ok = mod.set_files(FakeInputs([hidden]), ["/tmp/a.png"])
    assert ok is True
    assert hidden.files == ["/tmp/a.png"]


def test_set_files_returns_false_when_all_inputs_fail():
    class BrokenInput(FakeInput):
        def set_input_files(self, files):
            raise RuntimeError("blocked")

    ok = mod.set_files(FakeInputs([BrokenInput()]), ["/tmp/a.png"])
    assert ok is False
```

- [ ] **Step 2: Run the two tests and verify they fail because `set_files` does not exist yet**

Run: `"/Users/Shared/_AllDocMap/02_Project/gitee/james-python/.conda/bin/python" -m pytest james-work/python-app/tests/test_app_toutiao_ariticle_publisher.py -k set_files -v`

Expected: FAIL with `AttributeError` or import error because `set_files` has not been added yet.

- [ ] **Step 3: Implement a shared `set_files()` helper and reuse it from both upload paths**

```python
def set_files(inputs, files: List[str] | str) -> bool:
    for idx in range(inputs.count()):
        try:
            inputs.nth(idx).set_input_files(files)
            return True
        except Exception:
            continue
    return False


def _insert_images_to_editor(self, images: List[str]) -> int:
    ...
    if set_files(self.page.locator('input[type="file"]'), img_path):
        inserted += 1
        log(f"图片 {i+1} 上传成功")
        self.page.wait_for_timeout(2000)
    else:
        log("未找到可用文件输入框")
```

```python
def _upload_cover_image(self, cover_paths: List[str] = None) -> bool:
    ...
    if set_files(self.page.locator('input[type="file"]'), valid_paths):
        log(f"封面图片已上传: {len(valid_paths)} 张")
        self.page.wait_for_timeout(3000)
        return True
    ...
    return False
```

- [ ] **Step 4: Re-run the targeted tests and verify they pass**

Run: `"/Users/Shared/_AllDocMap/02_Project/gitee/james-python/.conda/bin/python" -m pytest james-work/python-app/tests/test_app_toutiao_ariticle_publisher.py -k set_files -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add james-work/python-app/app_toutiao_ariticle_publisher.py james-work/python-app/tests/test_app_toutiao_ariticle_publisher.py
git commit -m "fix: support hidden file inputs in toutiao uploads"
```

### Task 3: Thread `--headless` through the CLI and publisher entrypoints

**Files:**

- Modify: `james-work/python-app/app_toutiao_ariticle_publisher.py:1447-1697`
- Modify: `james-work/python-app/tests/test_app_toutiao_ariticle_publisher.py`
- Test: `james-work/python-app/tests/test_app_toutiao_ariticle_publisher.py`

- [ ] **Step 1: Write the failing test that proves `publish_single_file(..., headless=True)` must instantiate `ToutiaoPublisher(headless=True)`**

```python
def test_publish_single_file_threads_headless_flag(tmp_path, monkeypatch):
    md = tmp_path / "article.md"
    md.write_text("# 标题\n\n正文", encoding="utf-8")

    seen = {}

    class FakePublisher:
        def __init__(self, headless=False):
            seen["headless"] = headless

        def setup(self):
            return self

        def check_login_status(self):
            return True

        def publish_article(self, title, content, images, cover):
            return True, "发布成功", None

        def close(self):
            return None

    monkeypatch.setattr(mod, "PLAYWRIGHT_AVAILABLE", True)
    monkeypatch.setattr(mod, "ToutiaoPublisher", FakePublisher)

    code = mod.publish_single_file(str(md), headless=True)

    assert code == 0
    assert seen["headless"] is True
```

- [ ] **Step 2: Run the headless test and verify it fails because the function signature and constructor call still hard-code `False`**

Run: `"/Users/Shared/_AllDocMap/02_Project/gitee/james-python/.conda/bin/python" -m pytest james-work/python-app/tests/test_app_toutiao_ariticle_publisher.py::test_publish_single_file_threads_headless_flag -v`

Expected: FAIL because `publish_single_file()` does not accept `headless`, or because `ToutiaoPublisher(headless=False)` is still hard-coded.

- [ ] **Step 3: Add `headless` parameters to the entrypoints and pass `args.headless` from `main()`**

```python
def publish_single_file(markdown_path: str, images_dir: str = None, skip_published: bool = True, headless: bool = False) -> int:
    ...
    publisher = ToutiaoPublisher(headless=headless)


def publish_multiple_files(file_list: List[str], images_dir: str = None, headless: bool = False) -> int:
    ...
    publisher = ToutiaoPublisher(headless=headless)


def main():
    ...
    if args.list:
        return publish_multiple_files(args.list, args.images_dir, headless=args.headless)
    return publish_single_file(args.file, args.images_dir, skip_published=not args.no_skip, headless=args.headless)
```

- [ ] **Step 4: Re-run the headless test and verify it passes**

Run: `"/Users/Shared/_AllDocMap/02_Project/gitee/james-python/.conda/bin/python" -m pytest james-work/python-app/tests/test_app_toutiao_ariticle_publisher.py::test_publish_single_file_threads_headless_flag -v`

Expected: PASS.

- [ ] **Step 5: Run the full local test file and verify all tests are green**

Run: `"/Users/Shared/_AllDocMap/02_Project/gitee/james-python/.conda/bin/python" -m pytest james-work/python-app/tests/test_app_toutiao_ariticle_publisher.py -v`

Expected: PASS for the cover-selection, file-upload, and headless tests.

- [ ] **Step 6: Commit**

```bash
git add james-work/python-app/app_toutiao_ariticle_publisher.py james-work/python-app/tests/test_app_toutiao_ariticle_publisher.py
git commit -m "fix: thread headless mode through toutiao publisher cli"
```

### Task 4: Verify the real publish flow with the requested Python environment

**Files:**

- Modify: `james-work/python-app/app_toutiao_ariticle_publisher.py` (only if live verification exposes a specific reproducible failure)
- Test: `james-work/python-app/tests/test_app_toutiao_ariticle_publisher.py`
- Runtime data: `james-work/python-app/data/toutiao_cookies.json`
- Runtime data: `james-work/python-app/data/publish_status.json`

- [ ] **Step 1: Run the automated regression suite before opening the browser**

Run: `"/Users/Shared/_AllDocMap/02_Project/gitee/james-python/.conda/bin/python" -m pytest james-work/python-app/tests/test_app_toutiao_ariticle_publisher.py -v`

Expected: PASS.

- [ ] **Step 2: Start one real publish attempt with screenshots enabled and the requested interpreter**

Run: `"/Users/Shared/_AllDocMap/02_Project/gitee/james-python/.conda/bin/python" james-work/python-app/app_toutiao_ariticle_publisher.py -f "/Volumes/james1t/_AllDocMap/02_Project/mineru_proj/dt=2025-08-06/output_path/_LGTM_数据指标_快手--经营诊断与波动分析实践/auto/_LGTM_数据指标_快手--经营诊断与波动分析实践.md" --screenshot --debug`

Expected: A visible Chromium window opens, the script prompts for QR login if cookies are invalid, and the workflow proceeds through title, body, images, cover, and publish/draft verification.

- [ ] **Step 3: Complete QR login and observe the first end-to-end result**

Manual check:

```text
1. Scan the QR code in the opened browser.
2. Press Enter in the terminal after login succeeds.
3. Wait for either:
   - “✓ 发布成功!”, or
   - a verified draft success path where the manage page search finds the article.
```

Expected: The script exits with code 0 and updates `data/publish_status.json` with the processed file.

- [ ] **Step 4: If the live run exposes a reproducible bug in one of the known weak points, add one focused failing test before patching**

```python
def test_publish_confirm_clicks_visible_button(monkeypatch):
    page = FakePage()
    pub = mod.ToutiaoPublisher(headless=True)
    pub.page = page

    assert pub._click_publish() is True
    assert page.clicked == ["预览并发布", "确认发布"]
```

```python
def test_upload_cover_uses_second_file_input_when_first_fails(tmp_path, monkeypatch):
    first = FakeInputThatFails()
    second = FakeInput()
    page = FakePage(inputs=[first, second])
    pub = mod.ToutiaoPublisher(headless=True)
    pub.page = page

    img = tmp_path / "cover.png"
    img.write_bytes(b"img")

    assert pub._upload_cover_image([str(img)]) is True
    assert second.files == [str(img)]
```

Run one test that matches the reproduced live failure, for example:
`"/Users/Shared/_AllDocMap/02_Project/gitee/james-python/.conda/bin/python" -m pytest james-work/python-app/tests/test_app_toutiao_ariticle_publisher.py::test_publish_confirm_clicks_visible_button -v`

Expected: FAIL for the exact live bug you just reproduced.

- [ ] **Step 5: Apply the minimal patch for the live bug and re-run the targeted test plus the full file**

Run: `"/Users/Shared/_AllDocMap/02_Project/gitee/james-python/.conda/bin/python" -m pytest james-work/python-app/tests/test_app_toutiao_ariticle_publisher.py::test_publish_confirm_clicks_visible_button -v && "/Users/Shared/_AllDocMap/02_Project/gitee/james-python/.conda/bin/python" -m pytest james-work/python-app/tests/test_app_toutiao_ariticle_publisher.py -v`

Expected: PASS.

- [ ] **Step 6: Re-run the real publish command and verify either published or verified-draft success**

Run: `"/Users/Shared/_AllDocMap/02_Project/gitee/james-python/.conda/bin/python" james-work/python-app/app_toutiao_ariticle_publisher.py -f "/Volumes/james1t/_AllDocMap/02_Project/mineru_proj/dt=2025-08-06/output_path/_LGTM_数据指标_快手--经营诊断与波动分析实践/auto/_LGTM_数据指标_快手--经营诊断与波动分析实践.md" --screenshot --debug`

Expected: Exit code 0, screenshots only for debug evidence, and an entry under `published` in `data/publish_status.json`.

- [ ] **Step 7: Commit**

```bash
git add james-work/python-app/app_toutiao_ariticle_publisher.py james-work/python-app/tests/test_app_toutiao_ariticle_publisher.py james-work/python-app/data/publish_status.json
git commit -m "fix: complete live toutiao article publishing flow"
```
