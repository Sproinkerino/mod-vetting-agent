import pytest

from scripts.submit_indexnow import canonical_urls


def sitemap(*urls):
    body = "".join(f"<url><loc>{url}</loc></url>" for url in urls)
    return f'<?xml version="1.0"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{body}</urlset>'.encode()


def test_indexnow_accepts_only_canonical_public_urls():
    urls = ["https://reddit-pi.live/", "https://reddit-pi.live/guides/reddit-user-history/"]
    assert canonical_urls(sitemap(*urls)) == urls


@pytest.mark.parametrize("url", [
    "http://reddit-pi.live/",
    "https://mod-vetting-api.onrender.com/",
    "https://reddit-pi.live/?job=private",
    "https://reddit-pi.live/u/example/report",
])
def test_indexnow_rejects_noncanonical_or_private_urls(url):
    with pytest.raises(ValueError):
        canonical_urls(sitemap(url))
