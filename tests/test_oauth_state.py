from __future__ import annotations

import json
import time

import pytest
from fastapi import HTTPException

from apps.api.routes import oauth


def test_oauth_state_is_single_use_and_platform_bound(tmp_path, monkeypatch):
    monkeypatch.setattr(oauth, "STATE_DIR", tmp_path)
    state = "safe-state-123"
    oauth._save_state("youtube", state)

    oauth._consume_state("youtube", state)
    with pytest.raises(HTTPException) as exc:
        oauth._consume_state("youtube", state)
    assert exc.value.status_code == 400


def test_oauth_state_rejects_wrong_platform(tmp_path, monkeypatch):
    monkeypatch.setattr(oauth, "STATE_DIR", tmp_path)
    state = "safe-state-456"
    oauth._save_state("youtube", state)

    with pytest.raises(HTTPException) as exc:
        oauth._consume_state("tiktok", state)
    assert exc.value.status_code == 400
    assert (tmp_path / "youtube_safe-state-456.state").exists()


def test_oauth_state_expires_and_is_removed(tmp_path, monkeypatch):
    monkeypatch.setattr(oauth, "STATE_DIR", tmp_path)
    state = "safe-state-789"
    path = tmp_path / "youtube_safe-state-789.state"
    path.write_text(json.dumps({"state": state, "created_at": time.time() - oauth.STATE_TTL_SECONDS - 1}), encoding="utf-8")

    with pytest.raises(HTTPException) as exc:
        oauth._consume_state("youtube", state)
    assert exc.value.status_code == 400
    assert not path.exists()
