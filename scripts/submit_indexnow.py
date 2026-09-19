"""Submit the canonical sitemap URLs to IndexNow without exposing private routes."""
from __future__ import annotations

import argparse
from pathlib import Path
from urllib.parse import urlparse
import xml.etree.ElementTree as ET

import httpx


HOST = "reddit-pi.live"
KEY = "fcdab012c40d40cfa7e69483572672af"
KEY_LOCATION = f"https://{HOST}/{KEY}.txt"
ENDPOINT = "https://api.indexnow.org/indexnow"


def canonical_urls(sitemap_xml: bytes) -> list[str]:
    namespace = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    urls = [node.text or "" for node in ET.fromstring(sitemap_xml).findall(".//s:loc", namespace)]
    if not urls:
        raise ValueError("Sitemap contains no URLs")
    if len(urls) > 10_000:
        raise ValueError("IndexNow batch exceeds 10,000 URLs")
    for url in urls:
        parsed = urlparse(url)
        public_path = parsed.path == "/" or parsed.path.startswith("/guides/")
        if (parsed.scheme != "https" or parsed.hostname != HOST or parsed.query or parsed.fragment
                or not public_path):
            raise ValueError(f"Noncanonical sitemap URL: {url}")
    return urls


def submit(*, dry_run: bool = False) -> dict:
    with httpx.Client(timeout=45, follow_redirects=True) as client:
        sitemap = client.get(f"https://{HOST}/sitemap.xml")
        sitemap.raise_for_status()
        urls = canonical_urls(sitemap.content)
        key_response = client.get(KEY_LOCATION)
        key_response.raise_for_status()
        if key_response.text.strip() != KEY:
            raise ValueError("Hosted IndexNow key does not match")
        payload = {"host": HOST, "key": KEY, "keyLocation": KEY_LOCATION, "urlList": urls}
        if dry_run:
            return {"submitted": False, "url_count": len(urls), "urls": urls}
        response = client.post(ENDPOINT, json=payload)
        response.raise_for_status()
        return {"submitted": True, "url_count": len(urls), "status_code": response.status_code}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Submit reddit-pi's public sitemap URLs to IndexNow")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    print(submit(dry_run=args.dry_run))
