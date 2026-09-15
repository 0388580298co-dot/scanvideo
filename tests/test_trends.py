from apps.worker.services.trends import ConfiguredFeedTrendProvider, RssTrendProvider, TrendItem


def test_trends_are_sorted_by_score():
    provider = ConfiguredFeedTrendProvider([
        TrendItem("low", "https://example.com/low", 1),
        TrendItem("high", "https://example.com/high", 10),
    ])
    items = provider.discover(2)
    assert [item.title for item in items] == ["high", "low"]


def test_configured_provider_rejects_negative_limit():
    provider = ConfiguredFeedTrendProvider([TrendItem("item", "https://example.com/item", 1)])
    assert provider.discover(-1) == []


def test_rss_provider_parses_rss_and_scores_by_rank():
    payload = b'''<?xml version="1.0"?><rss><channel>
      <item><title>Second</title><link>https://example.com/2</link><rank>2</rank></item>
      <item><title>First</title><link>https://example.com/1</link><rank>1</rank></item>
    </channel></rss>'''
    items = RssTrendProvider._parse(payload, "https://feed.example.com/rss.xml")
    assert [item.title for item in sorted(items, key=lambda x: x.score, reverse=True)] == ["First", "Second"]
    assert items[0].source == "feed.example.com"


def test_rss_provider_parses_atom_href_links():
    payload = b'''<feed xmlns="http://www.w3.org/2005/Atom">
      <entry><title>Atom trend</title><link href="https://example.com/atom"/></entry>
    </feed>'''
    items = RssTrendProvider._parse(payload, "https://feed.example.com/atom.xml")
    assert len(items) == 1
    assert items[0].source_url == "https://example.com/atom"


def test_rss_provider_ignores_malformed_xml():
    assert RssTrendProvider._parse(b"<rss><broken>", "https://feed.example.com/rss.xml") == []


def test_rss_provider_rejects_non_http_sources():
    assert RssTrendProvider(["file:///etc/passwd"]).feed_urls == []
