"""Phase 5 · slice 1 — coverage (C1–C2) for the MERGED_CELL family. C3 N/A (no Q).

DoD C1 (승인본): "모든 c가 ≥1 strand OR Phase7 conditional-edge incoming ≥1". 본 family는
strand 경로로 충족. C2: 모든 edge traverse — family detect→fix edge + 출구 edge.
"""

import json
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
STRANDS = json.loads((PROJECT_ROOT / "spec" / "strands.json").read_text(encoding="utf-8"))

MERGED = [s for s in STRANDS if "c0341" in s["c_sequence"]]


def _edges(seq):
    return set(zip(seq, seq[1:]))


def test_c1_each_family_c_in_at_least_one_strand():
    """C1: c0340, c0341 각각 ≥1 strand에 등장(승인 DoD C1)."""
    assert sum("c0340" in s["c_sequence"] for s in STRANDS) >= 1
    assert sum("c0341" in s["c_sequence"] for s in STRANDS) >= 1


def test_c2_detect_to_fix_edge_traversed():
    """C2: c0340→c0341 edge가 traverse된다(실제로 549 strand 전부)."""
    count = sum(("c0340", "c0341") in _edges(s["c_sequence"]) for s in MERGED)
    assert count >= 1
    assert count == 549


def test_c2_fix_to_backbone_exit_edge():
    """C2: c0341→backbone 출구 edge가 ≥1 strand에 존재(family가 dead-end 아님)."""
    found = any(
        s["c_sequence"].index("c0341") + 1 < len(s["c_sequence"]) for s in MERGED
    )
    assert found


@pytest.mark.skip(reason="C3 N/A: MERGED_CELL family triggers no Q-code (can_route_to_q=[]).")
def test_c3_q_trigger_not_applicable():
    """C3(Q-trigger): MERGED_CELL family는 Q 없음 → 해당 없음(명시 skip)."""


# ===== Phase 5 · Slice 2 — TIME family coverage (C1–C3) =====
# ★ slice 1에서 N/A로 skip되던 C3가 TIME family(Q02/Q12 보유)에서 실제 발화한다.

TIME_NEW = ["c0213", "c0251", "c0310", "c0311", "c0314", "c0315"]
TIME_Q = [s for s in STRANDS if s.get("q_code") in ("Q02", "Q12")]


def test_c1_each_time_c_in_at_least_one_strand():
    """C1: 6개 신규 TIME c 각각 ≥1 strand에 등장."""
    for c in TIME_NEW:
        assert sum(c in s["c_sequence"] for s in STRANDS) >= 1, c


def test_c2_time_edges_traversed():
    """C2: detect→fix(c0310→c0311, c0314→c0315) + 축→ROUTE(c0203→c0251) edge가 traverse된다."""
    for a, b in [("c0310", "c0311"), ("c0314", "c0315"), ("c0203", "c0251")]:
        assert sum((a, b) in _edges(s["c_sequence"]) for s in STRANDS) >= 1, f"{a}->{b}"


def test_c3_q02_q12_triggered():
    """★ C3 활성화(slice 1 skip 대체): Q02·Q12가 strand에서 실제 trigger된다(falsifiable 388/397)."""
    q02 = sum(s.get("q_code") == "Q02" for s in STRANDS)
    q12 = sum(s.get("q_code") == "Q12" for s in STRANDS)
    assert q02 == 388, q02
    assert q12 == 397, q12


def test_c3_q_terminals_have_incoming_route_edge():
    """★ C3/D-S4: Q02·Q12 terminal은 c0251 ROUTE incoming edge ≥1 (고립 Q-terminal 0)."""
    assert TIME_Q
    for s in TIME_Q:
        assert s["c_sequence"][-1] == "c0251", s["sc_id"]


# ===== Phase 5 · Slice 3 — TIMEZONE family coverage (C1–C2; C3 N/A) =====
# ★ c0312/c0313 모두 can_route_to_q=[] → C3(Q-trigger) 해당 없음(slice 1 MERGED_CELL과 동형 skip).

TZ_NEW = ["c0312", "c0313"]
TZ = [s for s in STRANDS if "c0313" in s["c_sequence"]]


def test_c1_each_timezone_c_in_at_least_one_strand():
    """C1: c0312, c0313 각각 ≥1 strand에 등장(실제 532)."""
    for c in TZ_NEW:
        assert sum(c in s["c_sequence"] for s in STRANDS) >= 1, c


def test_c2_timezone_detect_to_fix_edge_traversed():
    """C2: c0312→c0313 edge가 traverse된다(실제로 532 strand 전부)."""
    count = sum(("c0312", "c0313") in _edges(s["c_sequence"]) for s in TZ)
    assert count >= 1
    assert count == 532


def test_c2_timezone_fix_to_backbone_exit_edge():
    """C2: c0313→backbone 출구 edge가 ≥1 strand에 존재(family가 dead-end 아님)."""
    found = any(
        s["c_sequence"].index("c0313") + 1 < len(s["c_sequence"]) for s in TZ
    )
    assert found


@pytest.mark.skip(reason="C3 N/A: TIMEZONE family triggers no Q-code (c0312/c0313 can_route_to_q=[]).")
def test_c3_timezone_not_applicable():
    """C3(Q-trigger): TIMEZONE family는 Q 없음 → 해당 없음(명시 skip)."""
