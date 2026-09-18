"""Read-only production crawler audit. No account scans or LLM requests."""
import argparse
import json
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse
import xml.etree.ElementTree as ET

import httpx


class Page(HTMLParser):
    def __init__(self):
        super().__init__()
        self.canonical = []
        self.descriptions = []
        self.h1 = 0
        self.links = []
        self.title = ""
        self.in_title = False
        self.assets = []
        self.og_url = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "title":
            self.in_title = True
        if tag == "meta" and attrs.get("property") == "og:url":
            self.og_url.append(attrs.get("content"))
        if tag == "script" and attrs.get("src"):
            self.assets.append(attrs["src"])
        if tag == "link" and attrs.get("rel") in {"stylesheet", "icon", "manifest", "apple-touch-icon"}:
            self.assets.append(attrs.get("href", ""))
        if tag == "link" and attrs.get("rel") == "canonical":
            self.canonical.append(attrs.get("href"))
        if tag == "meta" and attrs.get("name") == "description":
            self.descriptions.append(attrs.get("content"))
        if tag == "h1":
            self.h1 += 1
        if tag == "a" and attrs.get("href"):
            self.links.append(attrs["href"])

    def handle_data(self, data):
        if self.in_title:
            self.title += data

    def handle_endtag(self, tag):
        if tag == "title":
            self.in_title = False


def audit(base):
    evidence = []
    failures = []
    titles = set()
    descriptions = set()
    checked_links = set()
    with httpx.Client(timeout=45, follow_redirects=True) as client:
        sitemap = client.get(base + "/sitemap.xml")
        sitemap.raise_for_status()
        ns = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
        urls = [node.text for node in ET.fromstring(sitemap.content).findall(".//s:loc", ns)]
        assert urls and all(url.startswith("https://reddit-pi.live/") for url in urls)
        for canonical in urls:
            path = urlparse(canonical).path
            response = client.get(base + path)
            page = Page()
            page.feed(response.text)
            checks = {
                "status_200": response.status_code == 200,
                "html": "text/html" in response.headers.get("content-type", ""),
                "canonical": page.canonical == [canonical],
                "description": len(page.descriptions) == 1 and bool(page.descriptions[0]),
                "one_h1": page.h1 == 1,
                "indexable": "noindex" not in response.headers.get("x-robots-tag", ""),
                "internal_links": bool(page.links),
                "title_unique": bool(page.title.strip()) and page.title not in titles,
                "description_unique": bool(page.descriptions) and page.descriptions[0] not in descriptions,
                "social_url": page.og_url == [canonical],
            }
            titles.add(page.title)
            descriptions.update(page.descriptions)
            evidence.append({"path": path, "checks": checks})
            failures.extend(f"{path}: {key}" for key, ok in checks.items() if not ok)
            for link in set(page.links + page.assets):
                target = urljoin(base + path, link)
                if urlparse(target).netloc == urlparse(base).netloc and target not in checked_links:
                    checked_links.add(target)
                    linked = client.get(target)
                    if linked.status_code != 200:
                        failures.append(f"broken link: {target} ({linked.status_code})")
                    if urlparse(target).path.startswith("/assets/") and linked.status_code == 200:
                        if "immutable" not in linked.headers.get("cache-control", ""):
                            failures.append(f"asset cache policy: {target}")
                        if len(linked.content) > 1000 and linked.headers.get("content-encoding") != "gzip":
                            failures.append(f"asset compression: {target}")
        robots = client.get(base + "/robots.txt")
        if robots.status_code != 200 or "Sitemap: https://reddit-pi.live/sitemap.xml" not in robots.text:
            failures.append("robots sitemap declaration")
        for path in ("/?job=seo-audit-nonexistent", "/jobs/seo-audit-nonexistent", "/seo-audit-nonexistent"):
            response = client.get(base + path)
            if "noindex" not in response.headers.get("x-robots-tag", ""):
                failures.append(f"noindex missing: {path}")
            if path != "/?job=seo-audit-nonexistent" and response.status_code != 404:
                failures.append(f"not a real 404: {path}")
    return {"base": base, "pages": evidence, "failures": failures, "passed": not failures}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="https://reddit-pi.live")
    args = parser.parse_args()
    result = audit(args.base.rstrip("/"))
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result["passed"] else 1)
