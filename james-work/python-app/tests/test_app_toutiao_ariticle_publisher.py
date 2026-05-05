import importlib.util
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
FILE = ROOT / "james-work/python-app/app_toutiao_ariticle_publisher.py"
SPEC = importlib.util.spec_from_file_location("toutiao_publisher", FILE)
assert SPEC and SPEC.loader
mod = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = mod
SPEC.loader.exec_module(mod)


class FakePage:
    def goto(self, *args, **kwargs):
        return None

    def wait_for_timeout(self, *args, **kwargs):
        return None

    def evaluate(self, *args, **kwargs):
        return None

    def inner_text(self, *args, **kwargs):
        return ""

    def locator(self, *args, **kwargs):
        return FakeLocator()

    def get_by_role(self, *args, **kwargs):
        return FakeBtn()


class FakeBtn:
    def is_visible(self, timeout=None):
        return True

    def click(self, timeout=None):
        return None

    def bounding_box(self):
        return {"width": 120, "height": 32}


class FakeLocator:
    @property
    def first(self):
        return FakeBtn()

    def count(self):
        return 1

    def nth(self, idx):
        return FakeBtn()


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
    monkeypatch.setattr(pub, "_upload_cover_image", lambda covers: seen.setdefault("covers", covers) or True)
    monkeypatch.setattr(pub, "_wait_for_publish_complete", lambda: True)
    monkeypatch.setattr(pub, "_verify_article_on_manage_page", lambda title: True)

    ok, msg, url = pub.publish_article("标题", "正文", paths, None)

    assert ok is True
    assert msg == "发布成功"
    assert seen["covers"] == paths[:3]
