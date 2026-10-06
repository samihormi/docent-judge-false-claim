"""The static project page (docs/index.html) must match its generator and load nothing external.

Standard library only.
"""
import pathlib
import re
import subprocess
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]


class TestPage(unittest.TestCase):
    def test_page_is_current(self):
        before = (ROOT / "docs/index.html").read_bytes()
        subprocess.run([sys.executable, str(ROOT / "docs/make_page.py")], check=True, capture_output=True)
        self.assertEqual((ROOT / "docs/index.html").read_bytes(), before)

    def test_page_loads_nothing_external(self):
        page = (ROOT / "docs/index.html").read_text(encoding="utf-8")
        for pattern in (r"<script", r"<link\b", r"<iframe", r"@import", r"url\(", r"\bsrc=\"(?!img/)"):
            self.assertIsNone(re.search(pattern, page), pattern)
        for src in re.findall(r'src="([^"]+)"', page):
            self.assertTrue((ROOT / "docs" / src).is_file(), src)


if __name__ == "__main__":
    unittest.main()
