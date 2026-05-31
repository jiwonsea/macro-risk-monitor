"""Thin wrapper around the Codex CLI (`codex exec`) for non-interactive calls.

Codex is an optional external dependency used by data_selector.py to get a
second-model critique of proposed data series. When the binary is missing or
errors out, the caller degrades to a single-model (Claude-only) path — the
same graceful-degrade contract analyzer.py uses for the anthropic SDK.

The prompt is fed on stdin (``codex exec -``) rather than as an argv string to
sidestep Windows command-line length limits and quoting of Korean/newlines.
`codex exec` prints a session banner around the model reply, so callers parse
the reply with `extract_json` which is banner-tolerant.
"""

from __future__ import annotations

import json
import logging
import re
import shutil
import subprocess

logger = logging.getLogger(__name__)


class CodexUnavailable(RuntimeError):
    """codex CLI not installed, timed out, or returned a non-zero exit."""


_JSON_FENCE = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL)


def _resolve_codex() -> str | None:
    """Full path to the codex launcher. On Windows this resolves to ``codex.CMD``;
    subprocess must be given this resolved path, not the bare name ``codex``
    (the extensionless npm shim is not a runnable Win32 executable)."""

    return shutil.which("codex")


def codex_available() -> bool:
    return _resolve_codex() is not None


def run_codex(
    prompt: str, *, timeout: int = 180, reasoning_effort: str = "medium"
) -> str:
    """Run ``codex exec`` and return raw stdout. Raises CodexUnavailable on any
    failure so the caller can fall back without inspecting subprocess internals.
    """

    exe = _resolve_codex()
    if exe is None:
        raise CodexUnavailable("codex CLI not found on PATH")
    cmd = [
        exe,
        "exec",
        "--skip-git-repo-check",
        "-c",
        f"model_reasoning_effort={reasoning_effort}",
        "-",  # read instructions from stdin
    ]
    logger.info("codex exec (effort=%s, prompt=%d chars)", reasoning_effort, len(prompt))
    try:
        proc = subprocess.run(
            cmd,
            input=prompt,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=timeout,
        )
    except FileNotFoundError as exc:  # PATH race between which() and run()
        raise CodexUnavailable(f"codex CLI not executable: {exc}") from exc
    except subprocess.TimeoutExpired as exc:
        raise CodexUnavailable(f"codex exec timed out after {timeout}s") from exc
    if proc.returncode != 0:
        raise CodexUnavailable(
            f"codex exec exit {proc.returncode}: {(proc.stderr or '')[:300]}"
        )
    return proc.stdout or ""


def extract_json(codex_output: str) -> dict | None:
    """Pull the last fenced JSON object out of codex stdout.

    The reply is preferred as a ```json fenced block. If none is present, fall
    back to the outermost ``{...}`` span. The *last* parseable match wins so the
    model's final answer beats any JSON echoed earlier in its reasoning.
    """

    matches = _JSON_FENCE.findall(codex_output)
    if not matches:
        start, end = codex_output.find("{"), codex_output.rfind("}")
        if start != -1 and end > start:
            matches = [codex_output[start : end + 1]]
    for chunk in reversed(matches):
        try:
            return json.loads(chunk)
        except json.JSONDecodeError:
            continue
    return None
