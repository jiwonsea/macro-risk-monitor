"""HTML -> PDF via Chrome headless.

Mirrors the pattern used in career/cover-letters/.../_build_pdf.py.
Returns the PDF path on success or None when Chrome is unavailable so
callers can degrade gracefully (CI environments without Chrome).
"""

from __future__ import annotations

import logging
import os
import subprocess
from pathlib import Path

from .. import config as cfg

logger = logging.getLogger(__name__)


def html_to_pdf(html_path: Path, pdf_path: Path | None = None) -> Path | None:
    if not os.path.exists(cfg.CHROME_PATH):
        logger.warning("Chrome not found at %s; skipping PDF render", cfg.CHROME_PATH)
        return None

    pdf_path = pdf_path or (cfg.REPORTS_PDF_DIR / (html_path.stem + ".pdf"))
    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    pdf_path.unlink(missing_ok=True)

    cmd = [
        cfg.CHROME_PATH,
        "--headless=new",
        "--disable-gpu",
        "--no-pdf-header-footer",
        f"--print-to-pdf={pdf_path}",
        html_path.absolute().as_uri(),
    ]
    logger.info("chrome headless print-to-pdf %s -> %s", html_path.name, pdf_path.name)
    result = subprocess.run(
        cmd, capture_output=True, text=True, encoding="utf-8", errors="replace"
    )
    if not pdf_path.exists():
        logger.error(
            "PDF render failed: stdout=%s stderr=%s",
            result.stdout[:300],
            result.stderr[:300],
        )
        return None
    return pdf_path
