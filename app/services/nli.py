"""Entailment check: does a set of statements support a conclusion?

This is the test used at each step of the minimal sufficient set search. With a
real model it is a genuine Natural Language Inference judgement. Offline it uses a
transparent keyword-overlap heuristic so the algorithm still runs on CPU.
"""
from __future__ import annotations
from .text_utils import keywords


def entails_offline(support: list[str], conclusion: str) -> bool:
    """A simple, explainable stand-in for NLI. The conclusion is considered
    supported if the supporting statements together cover enough of its key ideas.
    """
    concl_kw = keywords(conclusion)
    if not concl_kw:
        return True
    covered = set()
    for s in support:
        covered |= keywords(s)
    coverage = len(concl_kw & covered) / len(concl_kw)
    return coverage >= 0.5
