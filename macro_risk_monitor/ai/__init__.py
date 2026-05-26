"""LLM analysis layer.

Three responsibilities:
    1. analyzer.py  — given Risk + Verdicts, produce the analytical markdown.
    2. risk_parser.py — given a free-form risk sentence, draft a Risk YAML skeleton.
    3. verifier.py  — cross-check that numeric quotes in LLM output are grounded
                       in the actual Readings (hallucination guard).
"""

from .analyzer import analyze, AnalyzeStub
from .risk_parser import parse_risk
from .verifier import verify_citations

__all__ = ["analyze", "AnalyzeStub", "parse_risk", "verify_citations"]
