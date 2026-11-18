"""Build the sitemap from the canonical pages in a finished publication."""
from html.parser import HTMLParser
from pathlib import Path
from xml.etree import ElementTree as ET


class PageHead(HTMLParser):
    def __init__(self):
        super().__init__()
        self.canonicals = []
        self.noindex = False

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if tag == "link" and "canonical" in attributes.get("rel", "").lower().split():
            self.canonicals.append(attributes.get("href", ""))
        if tag == "meta" and attributes.get("name", "").lower() == "robots":
            self.noindex |= "noindex" in attributes.get("content", "").lower()


def canonical_inventory(dist: Path, base: str) -> list[str]:
    urls = []
    for page in sorted(dist.rglob("*.html")):
        relative = page.relative_to(dist)
        head = PageHead()
        with page.open(encoding="utf-8") as stream:
            for line in stream:
                head.feed(line.partition("</head>")[0])
                if "</head>" in line:
                    break
        if not head.canonicals and relative.parts[0] in {"iiif", "editions", "pagefind"}:
            continue
        url = base + relative.as_posix()
        if head.canonicals != [url]:
            raise ValueError(f"{relative}: expected one canonical URL pointing to this page")
        if not head.noindex:
            urls.append(url)
    return sorted(urls)


def write_sitemap(dist: Path, base: str) -> None:
    urls = canonical_inventory(dist, base)
    root = ET.Element("urlset", xmlns="http://www.sitemaps.org/schemas/sitemap/0.9")
    for url in urls:
        ET.SubElement(ET.SubElement(root, "url"), "loc").text = url
    ET.indent(root)
    (dist / "sitemap.xml").write_bytes(ET.tostring(root, encoding="utf-8", xml_declaration=True) + b"\n")
    (dist / "robots.txt").write_text(
        f"User-agent: *\nAllow: /\nSitemap: {base}sitemap.xml\n", encoding="utf-8", newline="\n")
    print(f"Sitemap lists {len(urls)} canonical pages.")
