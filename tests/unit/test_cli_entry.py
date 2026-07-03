"""CLI executes as a script — guards the __main__-before-defs bug class."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_cli_help_runs_as_module():
    env = dict(os.environ, PYTHONPATH=str(ROOT))
    proc = subprocess.run(
        [sys.executable, "-m", "macro_risk_monitor.cli", "--help"],
        capture_output=True,
        text=True,
        cwd=ROOT,
        env=env,
        timeout=60,
    )
    assert proc.returncode == 0, proc.stderr
    for sub in ("run", "analyze", "backtest", "dashboard", "apply-review"):
        assert sub in proc.stdout
