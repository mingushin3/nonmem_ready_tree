"""Phase 5 · slice 1 — strand-level verification for the MERGED_CELL family.

Scope (PROMPTS L297/L298): downstream c's are still unimplemented, so a full
sc→terminal run is impossible. Verification is slice-scoped — static structural
checks over all 549 MERGED_CELL strands + dynamic execution of just the family
segment (c0340→c0341) on instantiated data. NotImplementedError = slice boundary.
"""

import json
from pathlib import Path

import pandas as pd
import pytest

from src.orchestrator import COST, run_strand, dispatch, record_path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
STRANDS = json.loads((PROJECT_ROOT / "spec" / "strands.json").read_text(encoding="utf-8"))

FAMILY = ["c0340", "c0341"]
MERGED = [s for s in STRANDS if "c0341" in s["c_sequence"]]


def _merged_df():
    """c0341이 forward-fill로 해소할 병합 잔존(dose 값-다음-NaN)을 가진 instantiated 데이터."""
    return pd.DataFrame({
        "subject_id": [1, 1, 1, 2, 2],
        "dose": [100.0, None, None, 200.0, None],
        "time_value": [0, 1, 2, 0, 1],
    })


def test_merged_strand_count():
    """MERGED_CELL family를 지나는 strand는 정확히 549개."""
    assert len(MERGED) == 549


def test_detection_precedes_fix_adjacent():
    """D-S1+D-S2: 모든 549 strand에서 c0340이 c0341 직전(인접, canonical order)."""
    for s in MERGED:
        seq = s["c_sequence"]
        assert "c0340" in seq, s["sc_id"]
        assert seq.index("c0340") == seq.index("c0341") - 1, s["sc_id"]


def test_family_cost_within_breakdown():
    """family 한계비용(1+3=4)이 strand의 L-4->L-5 cost_breakdown에 포함된다."""
    fam_cost = COST["c0340"] + COST["c0341"]
    assert fam_cost == 4
    for s in MERGED:
        assert s["cost_breakdown"].get("L-4->L-5", 0) >= fam_cost, s["sc_id"]


def test_family_actual_equals_best_dynamic():
    """동적 actual==best (family segment): orchestrator가 c0340→c0341만 실행하고 하류
    미구현 c에서 경계를 표식, family cost==4, 병합 잔존 0(silent no-op 0)."""
    for s in MERGED[:3]:
        df = _merged_df()
        rec = run_strand(s["c_sequence"], df)
        assert rec["actual_c_sequence"] == FAMILY, s["sc_id"]
        assert rec["total_cost"] == 4, s["sc_id"]
        assert rec["boundary_at"] is not None, s["sc_id"]   # 하류 미구현 경계
        out = rec["df"]
        # silent no-op 0: 병합 잔존이 실제로 해소됨
        assert not any((out[c].isna() & out[c].shift().notna()).any() for c in out.columns)
        assert list(out["dose"]) == [100.0, 100.0, 100.0, 200.0, 200.0]
        record_path(rec, s["sc_id"])


def test_actual_is_best_prefix():
    """actual_c_sequence는 best strand c_sequence의 prefix와 동일(분기 없음)."""
    for s in MERGED[:25]:
        df = _merged_df()
        rec = run_strand(s["c_sequence"], df)
        n = len(rec["actual_c_sequence"])
        assert rec["actual_c_sequence"] == s["c_sequence"][:n], s["sc_id"]
        assert rec["actual_c_sequence"] == FAMILY, s["sc_id"]


def test_d_s1_cut_vertex_negative():
    """★ D-S1: 감지(c0340) 없이 c0341 dispatch → RuntimeError (cut-vertex 증명)."""
    with pytest.raises(RuntimeError):
        dispatch("c0341", _merged_df(), {})
