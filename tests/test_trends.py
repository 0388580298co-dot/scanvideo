from apps.worker.services.trends import ConfiguredFeedTrendProvider, TrendItem


def test_trends_are_sorted_by_score():
    provider = ConfiguredFeedTrendProvider([
        TrendItem("low", "https://example.com/low", 1),
        TrendItem("high", "https://example.com/high", 10),
    ])
    items = provider.discover(2)
    assert [item.title for item in items] == ["high", "low"]
