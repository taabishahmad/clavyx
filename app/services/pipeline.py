"""The CLAVYX reasoning pipeline.

Seven stages turn a raw argument into the structured result that powers every
screen in the app:

    1. Decomposition        break the text into a conclusion and stated reasons
    2. Assumption excavation surface the unstated premises it depends on
    3. Minimal sufficient set find the smallest set of assumptions the conclusion needs
    4. Influence ordering    rank assumptions from most to least load bearing
    5. Opposing case         the strongest fair counter-argument (a steelman)
    6. Revision evidence     what proof would rationally change the conclusion
    7. Aggregation           assemble one result object

The minimal sufficient set search (stage 3) is a real greedy algorithm and runs
the same way no matter which model backs the entailment check.
"""
from __future__ import annotations
from .text_utils import split_sentences, keywords, overlap, looks_like_conclusion
from .nli import entails_offline
from . import llm_provider


# --------------------------------------------------------------------------
# Stage 3 algorithm: minimal sufficient assumption set (greedy elimination).
# Start with every assumption, then try to drop them one by one. Keep an
# assumption only if the conclusion stops being supported without it. What
# remains is a small set the conclusion genuinely cannot do without: the keys.
# --------------------------------------------------------------------------
def minimal_sufficient_set(premises, assumptions, conclusion, entails) -> list[str]:
    kept = list(assumptions)
    # Process from least to most relevant so the strongest keys survive.
    order = sorted(kept, key=lambda a: overlap(a, conclusion))
    for a in order:
        trial = [x for x in kept if x != a]
        if entails(premises + trial, conclusion):
            kept = trial  # 'a' was not necessary, drop it
    # Never return an empty set: if everything looked droppable, keep the single
    # most relevant assumption so the user still sees a keystone.
    if not kept and assumptions:
        kept = [max(assumptions, key=lambda a: overlap(a, conclusion))]
    return kept


def _influence_ranking(premises, assumptions, conclusion, entails) -> list[dict]:
    """Order assumptions by how much the conclusion depends on each. We express
    this as a rank, not a fake precise decimal, and label it an estimate. An
    assumption whose removal breaks support is 'critical'."""
    scored = []
    for a in assumptions:
        without = [x for x in assumptions if x != a]
        breaks = not entails(premises + without, conclusion)
        # tie-break by how central the wording is to the conclusion
        centrality = overlap(a, conclusion)
        scored.append({"text": a, "critical": breaks, "centrality": centrality})
    scored.sort(key=lambda d: (d["critical"], d["centrality"]), reverse=True)
    for i, d in enumerate(scored):
        d["rank"] = i + 1
        d["influence"] = "high" if d["critical"] else ("medium" if d["centrality"] > 0.12 else "low")
    return scored


# --------------------------------------------------------------------------
# Offline engine: produces a coherent analysis with no model and no network.
# It is intentionally transparent rather than clever. Comments mark where a real
# model does far better once an API key is set.
# --------------------------------------------------------------------------
def _offline(text: str) -> dict:
    sents = split_sentences(text)
    conclusion = next((s for s in sents if looks_like_conclusion(s)), sents[-1] if sents else text)
    premises = [s for s in sents if s != conclusion] or [conclusion]

    # Build candidate assumptions from the reasons given. A real model writes
    # sharper, genuinely unstated premises; here we template plausible ones.
    assumptions = []
    for pr in premises:
        assumptions.append(f"The claim that {pr.rstrip('.').lower()} is actually true and well supported.")
        assumptions.append(f"What holds for '{_short(pr)}' generalises to the situation in the conclusion.")
    kws = list(keywords(conclusion))[:3]
    if kws:
        assumptions.append("No stronger competing factor outweighs " + ", ".join(kws) + " here.")
    # de-duplicate while preserving order
    seen, uniq = set(), []
    for a in assumptions:
        if a.lower() not in seen:
            seen.add(a.lower()); uniq.append(a)
    assumptions = uniq[:6]

    minimal = minimal_sufficient_set(premises, assumptions, conclusion, entails_offline)
    ranked = _influence_ranking(premises, assumptions, conclusion, entails_offline)
    top = ranked[0]["text"] if ranked else (assumptions[0] if assumptions else conclusion)

    opposing = (
        f"A fair opponent would grant the intent but challenge the keystone. "
        f"If it turns out that {_short(top).lower()} does not hold, the conclusion loses most of its support. "
        f"They would argue the reasoning treats a convenient assumption as settled fact and would ask for direct evidence before accepting it."
    )
    weakest = {
        "text": top,
        "why": "The whole conclusion leans on this one assumption, yet it is asserted rather than shown.",
    }
    evidence = [
        {"assumption": a["text"],
         "evidence": f"Direct, comparable data showing whether '{_short(a['text']).lower()}' actually holds."}
        for a in ranked[:3]
    ]
    robustness = _robustness(len(minimal), len(assumptions))
    return _assemble(conclusion, premises, ranked, minimal, opposing, weakest, evidence, robustness, "offline engine")


def _short(s: str, n: int = 60) -> str:
    s = s.strip().rstrip(".")
    return (s[:n] + "...") if len(s) > n else s


def _robustness(minimal_count: int, total: int) -> int:
    # More load bearing assumptions relative to total = more fragile. An estimate.
    if total == 0:
        return 50
    frac = minimal_count / total
    return max(20, min(90, int(90 - frac * 60)))


def _assemble(conclusion, premises, ranked, minimal, opposing, weakest, evidence, robustness, engine) -> dict:
    return {
        "conclusion": conclusion,
        "premises": premises,
        "assumptions": ranked,          # each: text, rank, influence, critical
        "minimal_set": minimal,         # the keystones
        "opposing_case": opposing,
        "weakest_link": weakest,
        "evidence": evidence,
        "robustness": robustness,       # 0..100 estimate, clearly labelled in UI
        "engine": engine,
    }


# --------------------------------------------------------------------------
# Real-model path: ask the model for structured JSON, then run the same stage 3
# and stage 4 algorithms over its assumptions for consistency.
# --------------------------------------------------------------------------
_SYSTEM = (
    "You are CLAVYX, a rigorous and fair reasoning analyst. You never strawman. "
    "You surface the unstated assumptions an argument depends on and build the "
    "strongest honest opposing case. Always answer as strict JSON."
)

_USER_TMPL = """Analyse this argument and return JSON with these keys:
"conclusion": string,
"premises": array of strings (reasons actually stated),
"assumptions": array of 4 to 7 strings (unstated premises the argument depends on),
"opposing_case": string (the strongest fair counter-argument, no strawman),
"weakest_link": object with "text" and "why",
"evidence": array of objects with "assumption" and "evidence".

USER CONTENT:
\"\"\"{text}\"\"\"
"""


def _from_model(text: str) -> dict:
    data = llm_provider.complete_json(_SYSTEM, _USER_TMPL.format(text=text))
    conclusion = str(data.get("conclusion", "")).strip() or text[:120]
    premises = [str(p).strip() for p in data.get("premises", []) if str(p).strip()] or [conclusion]
    assumptions = [str(a).strip() for a in data.get("assumptions", []) if str(a).strip()]
    if not assumptions:
        raise llm_provider.ProviderError("model returned no assumptions")

    # Reuse our algorithms so the keystone and ordering are computed consistently.
    minimal = minimal_sufficient_set(premises, assumptions, conclusion, entails_offline)
    ranked = _influence_ranking(premises, assumptions, conclusion, entails_offline)

    opposing = str(data.get("opposing_case", "")).strip()
    wl = data.get("weakest_link") or {}
    weakest = {"text": str(wl.get("text", ranked[0]["text"])).strip(),
               "why": str(wl.get("why", "This step carries the most weight and is least supported.")).strip()}
    evidence = []
    for e in data.get("evidence", [])[:5]:
        if isinstance(e, dict) and e.get("evidence"):
            evidence.append({"assumption": str(e.get("assumption", "")).strip(),
                             "evidence": str(e.get("evidence", "")).strip()})
    if not evidence:
        evidence = [{"assumption": a["text"], "evidence": "Direct evidence testing this assumption."}
                    for a in ranked[:3]]
    robustness = _robustness(len(minimal), len(assumptions))
    return _assemble(conclusion, premises, ranked, minimal, opposing, weakest, evidence,
                     robustness, llm_provider.active_provider())


def analyse(text: str) -> dict:
    """Public entry point. Try the configured model; fall back to the offline
    engine on any problem so the user always gets a result."""
    if llm_provider.active_provider() != "mock":
        try:
            return _from_model(text)
        except Exception:
            pass  # network/key/parse issue: fall through to offline
    return _offline(text)


def suggest_title(text: str) -> str:
    first = split_sentences(text)[:1]
    base = first[0] if first else text
    return _short(base, 70)
