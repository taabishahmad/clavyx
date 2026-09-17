"""Small, dependency-free text helpers used by the offline engine."""
from __future__ import annotations
import re

_STOP = set("""a an the of to in on for and or but if is are was were be been being this that these those
it its as at by with from into about over under again further then once here there all any both each few more
most other some such no nor not only own same so than too very can will just should now we you they he she i our
your their his her because since therefore thus hence should must may might would could""".split())


def split_sentences(text: str) -> list[str]:
    text = re.sub(r"\s+", " ", text.strip())
    parts = re.split(r"(?<=[.!?])\s+", text)
    return [p.strip() for p in parts if p.strip()]


def keywords(text: str) -> set[str]:
    words = re.findall(r"[A-Za-z][A-Za-z\-']+", text.lower())
    return {w for w in words if len(w) > 2 and w not in _STOP}


def overlap(a: str, b: str) -> float:
    ka, kb = keywords(a), keywords(b)
    if not ka or not kb:
        return 0.0
    return len(ka & kb) / len(ka | kb)


def looks_like_conclusion(sentence: str) -> bool:
    s = sentence.lower()
    return any(m in s for m in (" should ", " must ", "therefore", " so ", " ought", " needs to", " has to")) \
        or s.startswith(("we should", "you should", "it should", "so ", "therefore"))
