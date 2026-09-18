from pathlib import Path
import xml.etree.ElementTree as ET

from fastapi.testclient import TestClient

from api import app


def test_analysis_and_error_responses_are_not_indexable():
    with TestClient(app) as client:
        for path in ("/health", "/jobs/nonexistent-seo-test", "/?job=private-test", "/no-such-seo-page"):
            response = client.get(path)
            assert response.headers.get("x-robots-tag") == "noindex, nofollow"
        assert "x-robots-tag" not in client.get("/").headers


def test_homepage_crawler_foundation():
    frontend = Path(__file__).resolve().parents[1] / "frontend"
    html = (frontend / "index.html").read_text(encoding="utf-8")
    assert '<link rel="canonical" href="https://reddit-pi.live/"' in html
    assert "<h1>" in html
    assert 'property="og:url"' in html
    robots = (frontend / "public/robots.txt").read_text()
    assert "Sitemap: https://reddit-pi.live/sitemap.xml" in robots
    assert "Disallow: /jobs" not in robots
    sitemap = ET.parse(frontend / "public/sitemap.xml")
    ns = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    assert [node.text for node in sitemap.findall(".//s:loc", ns)] == ["https://reddit-pi.live/"]


def test_built_guides_and_canonical_redirects():
    with TestClient(app) as client:
        for slug in ("reddit-user-history", "filter-reddit-history-by-subreddit", "verify-reddit-quotes", "methodology-and-data"):
            response = client.get(f"/guides/{slug}/")
            assert response.status_code == 200
            assert "<h1>" in response.text
            assert f'href="https://reddit-pi.live/guides/{slug}/"' in response.text
            assert "x-robots-tag" not in response.headers
            redirect = client.get(f"/guides/{slug}", follow_redirects=False)
            assert redirect.status_code in (301, 307, 308)
        missing = client.get("/guides/nonexistent/")
        assert missing.status_code == 404


def test_transfer_and_cache_policies():
    dist = Path(__file__).resolve().parents[1] / "frontend/dist"
    asset = next((dist / "assets").glob("*.js"))
    with TestClient(app) as client:
        response = client.get(f"/assets/{asset.name}", headers={"Accept-Encoding": "gzip"})
        assert response.status_code == 200
        assert response.headers["content-encoding"] == "gzip"
        assert response.headers["cache-control"] == "public, max-age=31536000, immutable"
        assert client.get("/").headers["cache-control"] == "no-cache"
        assert client.get("/?job=private").headers["cache-control"] == "no-store"
        assert client.get("/jobs/missing").headers["cache-control"] == "no-store"
