"""Codex CLI wrapper unit tests — subprocess fully mocked, no real codex call."""

from __future__ import annotations

import subprocess

import pytest

from macro_risk_monitor.ai import codex_client as cc


class _Proc:
    def __init__(self, returncode=0, stdout="", stderr=""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def test_codex_available(monkeypatch):
    monkeypatch.setattr(cc.shutil, "which", lambda name: "/usr/bin/codex")
    assert cc.codex_available()
    monkeypatch.setattr(cc.shutil, "which", lambda name: None)
    assert not cc.codex_available()


def test_run_codex_unavailable_when_missing(monkeypatch):
    monkeypatch.setattr(cc.shutil, "which", lambda name: None)
    with pytest.raises(cc.CodexUnavailable):
        cc.run_codex("hi")


def test_run_codex_success(monkeypatch):
    monkeypatch.setattr(cc.shutil, "which", lambda name: "/usr/bin/codex")
    monkeypatch.setattr(cc.subprocess, "run", lambda *a, **k: _Proc(stdout="banner\ncodex\nresult"))
    assert cc.run_codex("hi") == "banner\ncodex\nresult"


def test_run_codex_nonzero_raises(monkeypatch):
    monkeypatch.setattr(cc.shutil, "which", lambda name: "/usr/bin/codex")
    monkeypatch.setattr(cc.subprocess, "run", lambda *a, **k: _Proc(returncode=1, stderr="boom"))
    with pytest.raises(cc.CodexUnavailable):
        cc.run_codex("hi")


def test_run_codex_timeout_raises(monkeypatch):
    monkeypatch.setattr(cc.shutil, "which", lambda name: "/usr/bin/codex")

    def boom(*a, **k):
        raise subprocess.TimeoutExpired(cmd="codex", timeout=1)

    monkeypatch.setattr(cc.subprocess, "run", boom)
    with pytest.raises(cc.CodexUnavailable):
        cc.run_codex("hi", timeout=1)


def test_extract_json_fenced():
    out = 'banner\ncodex\n```json\n{"a": 1}\n```\ntokens used\n5,000'
    assert cc.extract_json(out) == {"a": 1}


def test_extract_json_last_match_wins():
    out = '```json\n{"a": 1}\n```\nmore\n```json\n{"a": 2}\n```'
    assert cc.extract_json(out) == {"a": 2}


def test_extract_json_braces_fallback():
    assert cc.extract_json('noise {"b": 3} trailing') == {"b": 3}


def test_extract_json_none():
    assert cc.extract_json("no json at all") is None
