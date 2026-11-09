"""Sync the live homepage's selected highlights, preserving all other README text."""

import argparse
from html import escape
from html.parser import HTMLParser
from pathlib import Path
import re
from urllib.parse import quote, urljoin, urlsplit
from urllib.request import Request, urlopen

SITE = "https://www.jacquesblom.com/"
START = "<!-- WEBSITE HIGHLIGHTS START -->"
END = "<!-- WEBSITE HIGHLIGHTS END -->"
MAX_BYTES = 1_000_000
VOID_TAGS = set("area base br col embed hr img input link meta param source track wbr".split())


class HighlightsParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack = []
        self.section_depth = None
        self.article_depth = None
        self.current = None
        self.items = []
        self.sections = 0

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag in VOID_TAGS:
            return
        self.stack.append((tag, attrs))
        if tag == "section" and attrs.get("aria-labelledby") == "library-heading":
            self.sections += 1
            self.section_depth = len(self.stack)
        if self.section_depth is None:
            return
        if tag == "article":
            if self.current is not None:
                raise ValueError("Nested highlight articles are not supported")
            self.article_depth = len(self.stack)
            self.current = {"title": [], "meta": [], "description": [], "url": ""}
        if self.current is not None and tag == "a" and any(t == "h3" for t, _ in self.stack):
            self.current["url"] = attrs.get("href", "")

    def handle_data(self, data):
        if self.current is None:
            return
        ancestors = self.stack[self.article_depth:]
        if any(tag in {"script", "style"} for tag, _ in ancestors):
            return
        if any(tag == "h3" for tag, _ in ancestors):
            self.current["title"].append(data)
        elif any("selected-meta" in attrs.get("class", "").split() for _, attrs in ancestors):
            self.current["meta"].append(data)
        elif any(tag == "p" for tag, _ in ancestors):
            self.current["description"].append(data)

    def handle_endtag(self, tag):
        if tag in VOID_TAGS:
            return
        if not self.stack or self.stack[-1][0] != tag:
            raise ValueError("Unexpected homepage markup; keeping the existing README")
        if len(self.stack) == self.article_depth:
            self.items.append(self.current)
            self.current = None
            self.article_depth = None
        if len(self.stack) == self.section_depth:
            self.section_depth = None
        self.stack.pop()


def markdown_text(value):
    value = escape(" ".join(value.split()), quote=False)
    return re.sub(r"([\\`*_{}\[\]()#!|~])", r"\\\1", value)


def render_highlights(html):
    parser = HighlightsParser()
    parser.feed(html)
    parser.close()
    if parser.stack or parser.sections != 1 or not parser.items:
        raise ValueError("Expected one complete, nonempty homepage highlights section")
    rows = []
    seen = set()
    for item in parser.items:
        fields = {key: " ".join("".join(item[key]).split()) for key in ("title", "meta", "description")}
        if not all(fields.values()) or not item["url"]:
            raise ValueError("A homepage highlight is missing its title, date/type, description, or link")
        url = urljoin(SITE, item["url"])
        parsed = urlsplit(url)
        if (parsed.scheme != "https" or parsed.netloc != "www.jacquesblom.com"
                or not parsed.path.startswith(("/work/", "/library/"))):
            raise ValueError("A highlight must link to published work or library content on the website")
        if url in seen:
            continue
        seen.add(url)
        safe_url = quote(url, safe="/:?=&%#-._~")
        rows.append(
            f"- **[{markdown_text(fields['title'])}]({safe_url})** — {markdown_text(fields['meta'])}\n"
            f"  {markdown_text(fields['description'])}"
        )
    return "\n\n".join(rows[:3])


def update_readme(readme, highlights):
    if readme.count(START) != 1 or readme.count(END) != 1:
        raise ValueError("README must contain exactly one pair of website highlight markers")
    start = readme.index(START) + len(START)
    end = readme.index(END)
    if start > end:
        raise ValueError("README highlight markers are reversed")
    return readme[:start] + "\n\n" + highlights + "\n\n" + readme[end:]


def fetch_homepage():
    request = Request(SITE, headers={"User-Agent": "jacques-blom-profile-sync/1.0"})
    with urlopen(request, timeout=30) as response:
        if urlsplit(response.url).netloc != "www.jacquesblom.com":
            raise ValueError("Homepage redirected to an unexpected host")
        if response.headers.get_content_type() != "text/html":
            raise ValueError("Homepage did not return HTML")
        data = response.read(MAX_BYTES + 1)
        if len(data) > MAX_BYTES:
            raise ValueError("Homepage response is too large")
        return data.decode("utf-8")


def main():
    args = argparse.ArgumentParser(description=__doc__)
    args.add_argument("--html", type=Path, help="Use a saved homepage for offline verification")
    args.add_argument("--readme", type=Path, default=Path(__file__).resolve().parents[1] / "README.md")
    options = args.parse_args()
    original = options.readme.read_text(encoding="utf-8")
    html = options.html.read_text(encoding="utf-8") if options.html else fetch_homepage()
    updated = update_readme(original, render_highlights(html))
    if updated != original:
        options.readme.write_text(updated, encoding="utf-8")
        print("Updated website highlights")
    else:
        print("Website highlights are unchanged")


if __name__ == "__main__":
    main()
