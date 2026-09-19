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
    assert '"@type":"WebSite"' in html
    assert "meta.name = 'robots'" in html
    assert "has('job')" in html
    assert "IBM+Plex" not in html
    assert "family=Inter" in html
    css = (frontend / "src/index.css").read_text(encoding="utf-8")
    assert "@import" not in css
    robots = (frontend / "public/robots.txt").read_text()
    assert "Sitemap: https://reddit-pi.live/sitemap.xml" in robots
    assert "Disallow: /jobs" not in robots
    sitemap = ET.parse(frontend / "public/sitemap.xml")
    ns = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    assert [node.text for node in sitemap.findall(".//s:loc", ns)] == ["https://reddit-pi.live/"]


def test_built_guides_and_canonical_redirects():
    with TestClient(app) as client:
        for slug in ("reddit-user-history", "filter-reddit-history-by-subreddit", "verify-reddit-quotes", "methodology-and-data",
                     "why-reddit-history-is-missing", "cached-vs-fresh-reddit-search"):
            response = client.get(f"/guides/{slug}/")
            assert response.status_code == 200
            assert "<h1>" in response.text
            assert f'href="https://reddit-pi.live/guides/{slug}/"' in response.text
            assert "x-robots-tag" not in response.headers
            redirect = client.get(f"/guides/{slug}", follow_redirects=False)
            assert redirect.status_code in (301, 307, 308)
        missing = client.get("/guides/nonexistent/")
        assert missing.status_code == 404


def test_render_public_pages_permanently_redirect_to_canonical_host():
    with TestClient(app, base_url="https://mod-vetting-frontend.onrender.com") as client:
        home = client.get("/?utm_source=test", follow_redirects=False)
        assert home.status_code == 308
        assert home.headers["location"] == "https://reddit-pi.live/?utm_source=test"
        guide = client.head("/guides/reddit-user-history/", follow_redirects=False)
        assert guide.status_code == 308
        assert guide.headers["location"] == "https://reddit-pi.live/guides/reddit-user-history/"
        assert client.get("/health", follow_redirects=False).status_code == 200
        assert client.post("/jobs", json={}).status_code != 308


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
