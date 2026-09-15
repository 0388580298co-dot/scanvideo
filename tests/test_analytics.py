from unittest.mock import patch

import pytest

from apps.worker.services.analytics import AnalyticsError, refresh_metrics


def test_unsupported_tiktok_metrics_are_explicit():
    with pytest.raises(AnalyticsError, match="TikTok metrics provider"):
        refresh_metrics("tiktok", "publish-id")


def test_youtube_metrics_adapter_is_used():
    expected = {"views": 10, "likes": 2, "comments": 1, "source": "youtube_data_api_v3"}
    with patch("apps.worker.services.analytics.youtube_metrics", return_value=expected):
        assert refresh_metrics("youtube", "abc") == expected
