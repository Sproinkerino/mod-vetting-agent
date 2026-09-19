from scripts.audit_seo import Page, structured_data_valid


def test_parser_captures_crawler_metadata_and_assets():
    page = Page()
    page.feed('<title>History &amp; Quotes</title><h1>History</h1>'
              '<meta name="description" content="Read history">'
              '<meta property="og:url" content="https://reddit-pi.live/">'
              '<link rel="canonical" href="https://reddit-pi.live/">'
              '<link rel="stylesheet" href="/assets/app.css">'
              '<script src="/assets/app.js"></script>'
              '<link rel="manifest" href="/manifest.webmanifest">'
              '<script type="application/ld+json">{"@context":"https://schema.org","@type":"WebSite","url":"https://reddit-pi.live/"}</script>'
              '<a href="/guides/reddit-user-history/">Guide</a>')
    assert page.title == "History & Quotes"
    assert page.h1 == 1
    assert page.canonical == page.og_url == ["https://reddit-pi.live/"]
    assert page.descriptions == ["Read history"]
    assert page.assets == ["/assets/app.css", "/assets/app.js", "/manifest.webmanifest"]
    assert page.links == ["/guides/reddit-user-history/"]
    assert page.json_ld[0]["@type"] == "WebSite"
    assert structured_data_valid(page, "https://reddit-pi.live/")


def test_parser_validates_guide_article_and_breadcrumb_graph():
    page = Page()
    page.feed('<script type="application/ld+json">{"@context":"https://schema.org","@graph":['
              '{"@type":"BreadcrumbList","itemListElement":[]},'
              '{"@type":"Article","url":"https://reddit-pi.live/guides/example/","headline":"Example","dateModified":"2026-09-19"}'
              ']}</script>')
    assert structured_data_valid(page, "https://reddit-pi.live/guides/example/")
    assert not structured_data_valid(page, "https://reddit-pi.live/guides/different/")
