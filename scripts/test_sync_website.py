import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from sync_website import END, START, markdown_text, render_highlights, update_readme


def article(title="Counted", url="/work/counted/", meta="Project · 2026–present", description="Election results."):
    return (
        f'<article><p class="selected-meta">{meta}</p>'
        f'<h3><a href="{url}">{title}</a></h3><p>{description}</p></article>'
    )


def homepage(*items):
    return '<section aria-labelledby="library-heading"><div>' + "".join(items) + '</div></section>'


class SyncTests(unittest.TestCase):
    def test_three_highlights_keep_editorial_order_dates_and_links(self):
        result = render_highlights(homepage(
            article(),
            article("Hooks", "/library/hooks/", "Video · 29 Mar 2021"),
            article("Video rendering", "/library/rendering/", "Talk · 25 Dec 2021"),
            article("MSW", "/library/msw/"),
        ))
        self.assertEqual(result.count("- **["), 3)
        self.assertIn("https://www.jacquesblom.com/work/counted/", result)
        self.assertIn("Video · 29 Mar 2021", result)
        self.assertLess(result.index("Hooks"), result.index("Video rendering"))
        self.assertNotIn("MSW", result)

    def test_decodes_entities_and_escapes_markdown_and_html(self):
        result = render_highlights(homepage(article(
            title="Hooks &amp; &lt;script&gt; [example] *demo*",
            description="A <em>small</em> example.",
        )))
        self.assertIn("Hooks &amp; &lt;script&gt; \\[example\\] \\*demo\\*", result)
        self.assertIn("A small example.", result)
        self.assertNotIn("<script>", result)
        self.assertEqual(markdown_text("one\ntwo"), "one two")

    def test_ignores_unfeatured_articles_and_deduplicates(self):
        result = render_highlights(article("Outside") + homepage(article(), article()))
        self.assertNotIn("Outside", result)
        self.assertEqual(result.count("- **["), 1)

    def test_preserves_manual_text_and_is_idempotent(self):
        original = f"# Story\n\n{START}\nold\n{END}\n\nPersonal links.\n"
        updated = update_readme(original, "New highlights")
        self.assertEqual(updated.split(START)[0], original.split(START)[0])
        self.assertEqual(updated.split(END)[1], original.split(END)[1])
        self.assertEqual(update_readme(updated, "New highlights"), updated)

    def test_refuses_invalid_marker_layouts(self):
        for text in ("No markers", START, END + START, START + END + START):
            with self.subTest(text=text), self.assertRaises(ValueError):
                update_readme(text, "New")

    def test_refuses_empty_incomplete_or_changed_markup(self):
        for html in (
            homepage(),
            homepage(article()).replace("library-heading", "new-heading"),
            homepage(article(description="")),
            homepage(article(url="")),
            homepage(article()) + homepage(article()),
            homepage(article())[:-10],
        ):
            with self.subTest(html=html), self.assertRaises(ValueError):
                render_highlights(html)

    def test_refuses_links_outside_published_website_content(self):
        for url in ("javascript:alert(1)", "https://example.com/library/item/",
                    "//evil.example/work/item/", "http://www.jacquesblom.com/work/item/",
                    "/about/", "https://www.jacquesblom.com.evil.example/work/item/"):
            with self.subTest(url=url), self.assertRaises(ValueError):
                render_highlights(homepage(article(url=url)))

    def test_failed_extraction_leaves_file_untouched(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            readme = path / "README.md"
            original = f"My story\n{START}\nExisting highlights\n{END}\n"
            readme.write_text(original, encoding="utf-8")
            html = path / "homepage.html"
            html.write_text(homepage(), encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(Path(__file__).with_name("sync_website.py")),
                 "--html", str(html), "--readme", str(readme)],
                capture_output=True, text=True,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(readme.read_text(encoding="utf-8"), original)


if __name__ == "__main__":
    unittest.main()
