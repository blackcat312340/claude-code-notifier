"""Tests for the notifier-feishu CLI config layer (setup/status).

Covers atomic secret-file writing, POSIX permissions, and the
load-time guards shared by status/test commands.
"""
import json
import os
import stat

import pytest

from notifier.core.feishu import load_feishu_config
from notifier.cli.feishu import save_feishu_config


def test_save_and_load_roundtrip(temp_dir):
    path = temp_dir / "feishu.json"
    save_feishu_config({"webhook": "https://open.feishu.cn/open-apis/bot/v2/hook/t", "secret": "s", "device": "pc-a"}, path=path)
    loaded = load_feishu_config(path)
    assert loaded["webhook"].startswith("https://open.feishu.cn")
    assert loaded["secret"] == "s"
    assert loaded["device"] == "pc-a"


def test_saved_config_is_mode_0600_on_posix(temp_dir):
    if os.name == "nt":
        pytest.skip("POSIX-only permission check")
    path = temp_dir / "feishu.json"
    save_feishu_config({"webhook": "w", "secret": "s"}, path=path)
    mode = stat.S_IMODE(path.stat().st_mode)
    assert mode == 0o600


def test_load_rejects_oversize_file(temp_dir):
    path = temp_dir / "feishu.json"
    path.write_text("x" * 5000, encoding="utf-8")
    assert load_feishu_config(path) == {}


def test_load_rejects_invalid_json(temp_dir):
    path = temp_dir / "feishu.json"
    path.write_text("not json", encoding="utf-8")
    assert load_feishu_config(path) == {}


def test_load_rejects_non_dict_json(temp_dir):
    path = temp_dir / "feishu.json"
    path.write_text("[1, 2, 3]", encoding="utf-8")
    assert load_feishu_config(path) == {}


def test_save_is_atomic_no_temp_left_behind(temp_dir):
    path = temp_dir / "feishu.json"
    save_feishu_config({"webhook": "w"}, path=path)
    leftovers = [p.name for p in temp_dir.iterdir() if p.name.startswith(".feishu-")]
    assert leftovers == []
