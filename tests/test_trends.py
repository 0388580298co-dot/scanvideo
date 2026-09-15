from apps.worker.services.trends import ConfiguredFeedTrendProvider, RssTrendProvider, TrendItem


def test_trends_are_sorted_by_score():
    provider = ConfiguredFeedTrendProvider([
        TrendItem("low", "https://example.com/low", 1),
        TrendItem("high", "https://example.com/high", 10),
    ])
    items = provider.discover(2)
    assert [item.title for item in items] == ["high", "low"]


def test_rss_provider_parses_rss_and_scores_by_rank():
    payload = b'''<?xml version="1.0"?><rss><channel>
      <item><title>Second</title><link>https://example.com/2</link><rank>2</rank></item>
      <item><title>First</title><link>https://example.com/1</link><rank>1</rank></item>
    </channel></rss>'''
    items = RssTrendProvider._parse(payload, "https://feed.example.com/rss.xml")
    assert [item.title for item in sorted(items, key=lambda x: x.score, reverse=True)] == ["First", "Second"]
    assert items[0].source == "feed.example.com"


def test_rss_provider_rejects_non_http_sources():
    assert RssTrendProvider(["file:///etc/passwd"]).feed_urls == []
