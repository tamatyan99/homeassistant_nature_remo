"""Tests for HACS repository configuration."""

from __future__ import annotations

import json
from pathlib import Path


def test_hacs_config_uses_repository_installation() -> None:
    """Do not require release assets before this repository publishes releases."""
    hacs_config = json.loads(Path("hacs.json").read_text(encoding="utf-8"))

    assert hacs_config["content_in_root"] is False
    assert hacs_config["homeassistant"] == "2023.8.0"
    assert hacs_config.get("zip_release") is not True
    assert "filename" not in hacs_config
