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
