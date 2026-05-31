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

from src.orchestrator import COST, run_strand, dispatch, record_path, REGISTRY

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


# ===== Phase 5 · Slice 2 — TIME family (Q02/Q12 라우팅 검증) =====

TIME_Q = [s for s in STRANDS if s.get("q_code") in ("Q02", "Q12")]


def test_q02_q12_strand_count():
    """Q02/Q12로 라우팅되는 strand는 정확히 785개(falsifiable: Q02 388 + Q12 397)."""
    assert len(TIME_Q) == 785


def test_q02_q12_routed_by_c0251_last():
    """★ 고립 Q-terminal 0의 핵심: Q02/Q12 strand 전부 c0251(ROUTE)을 last-c·QUARANTINE으로 둔다.
    (c0019가 아니라 c0251이 실제 라우터 — 발주 멘탈모델 교정, GAP-26.)"""
    for s in TIME_Q:
        assert s["c_sequence"][-1] == "c0251", s["sc_id"]
        assert s["terminal"] == "QUARANTINE", s["sc_id"]


def test_c0203_precedes_c0251_d_s1():
    """D-S1: 모든 Q02/Q12 strand에서 c0251의 detection producer c0203이 선행한다."""
    for s in TIME_Q:
        seq = s["c_sequence"]
        assert "c0203" in seq, s["sc_id"]
        assert seq.index("c0203") < seq.index("c0251"), s["sc_id"]


def test_route_ambiguous_to_q02_dynamic():
    """★ 핵심목표: orchestrator가 a3_state=AMBIGUOUS(c0203 생산) → c0251 → Q02 terminal 도출."""
    rec = run_strand(["c0203", "c0251"], pd.DataFrame({"time_value": [0, 1, 2]}), {"time_policy": "ambiguous"})
    assert rec["actual_c_sequence"] == ["c0203", "c0251"]
    assert rec["terminal"] == "QUARANTINE"
    assert rec["q_code"] == "Q02"
    # cost = Σc.cost (Q.routing_cost 비가산 — strands.json 정합, delta=0)
    assert rec["total_cost"] == COST["c0203"] + COST["c0251"]
    record_path(rec, "slice2_route_ambiguous")


def test_route_unrecoverable_to_q12_dynamic():
    """★ 핵심목표: a3_state=UNRECOVERABLE → c0251 → Q12 (snippet 'INVALID' 산문 무시; SSOT/GAP-7)."""
    rec = run_strand(["c0203", "c0251"], pd.DataFrame({"time_value": [0, 1, 2]}), {"time_policy": "unrecoverable"})
    assert rec["actual_c_sequence"] == ["c0203", "c0251"]
    assert rec["terminal"] == "QUARANTINE"
    assert rec["q_code"] == "Q12"
    record_path(rec, "slice2_route_unrecoverable")


def test_q_terminals_reachable_not_isolated():
    """★ D-S4 고립 Q-terminal 0: Q02·Q12 모두 동적 orchestrator로 도달(C3 Q-trigger 발화)."""
    reached = set()
    for policy in ("ambiguous", "unrecoverable"):
        rec = run_strand(["c0203", "c0251"], pd.DataFrame({"time_value": [0, 1]}), {"time_policy": policy})
        reached.add(rec["q_code"])
    assert reached == {"Q02", "Q12"}


def test_d_s1_route_cut_vertex_negative():
    """★ D-S1: detection(c0203) 없이 c0251(route) dispatch → RuntimeError (cut-vertex 증명)."""
    with pytest.raises(RuntimeError):
        dispatch("c0251", pd.DataFrame({"time_value": [0]}), {"a3_state": "AMBIGUOUS"})


def test_time_format_production_chain_dynamic():
    """★ time_value 생산(GAP-18 종결): c0310→c0311이 clock 문자열을 numeric으로 실제 변환 + silent no-op 0."""
    df = pd.DataFrame({"time_value": ["0:00", "1:30", "3:00"]})
    rec = run_strand(["c0310", "c0311"], df, {})
    assert rec["actual_c_sequence"] == ["c0310", "c0311"]
    assert rec["boundary_at"] is None
    out = rec["df"]
    assert out["time_value"].apply(lambda x: isinstance(x, (int, float))).all()
    assert list(out["time_value"]) == [0.0, 1.5, 3.0]   # silent no-op이면 문자열 잔존 → 실패


def test_time_anchor_production_chain_dynamic():
    """c0314→c0315가 anchor 토큰(Day N)을 비교가능 numeric(hours)으로 파싱."""
    df = pd.DataFrame({"time_value": [0, 1, 2], "time_anchor": ["Day 1", "Day 2", "Day 3"]})
    rec = run_strand(["c0314", "c0315"], df, {})
    assert rec["actual_c_sequence"] == ["c0314", "c0315"]
    out = rec["df"]
    assert list(out["time_anchor_parsed"]) == [0.0, 24.0, 48.0]


def test_d_s1_convert_cut_vertex_negative():
    """★ D-S1: detection(c0310) 없이 c0311(transform) dispatch → RuntimeError."""
    with pytest.raises(RuntimeError):
        dispatch("c0311", pd.DataFrame({"time_value": ["0:00"]}), {"time_format_detected": "clock"})


# ===== Phase 5 · Slice 3 — TIMEZONE family (c0312 DETECT + c0313 NORMALIZE; no Q) =====

TZ = [s for s in STRANDS if "c0313" in s["c_sequence"]]
TZ_PAIR = ["c0312", "c0313"]


def _mixed_tz_df():
    """혼합 시간대(UTC+KST) — c0313이 단일 tz로 실제 정규화해야 silent no-op 0."""
    return pd.DataFrame({"time_value": ["00:00 UTC", "09:00 KST", "12:00 KST"]})


def test_timezone_strand_count():
    """TIMEZONE family를 지나는 strand는 정확히 532개."""
    assert len(TZ) == 532


def test_timezone_detection_precedes_fix_adjacent():
    """D-S1+D-S2: 모든 532 strand에서 c0312가 c0313 직전(인접, canonical order)."""
    for s in TZ:
        seq = s["c_sequence"]
        assert "c0312" in seq, s["sc_id"]
        assert seq.index("c0312") == seq.index("c0313") - 1, s["sc_id"]


def test_timezone_family_cost_within_breakdown():
    """family 한계비용(1+2=3)이 strand의 L-4->L-5 cost_breakdown에 포함된다."""
    fam_cost = COST["c0312"] + COST["c0313"]
    assert fam_cost == 3
    for s in TZ:
        assert s["cost_breakdown"].get("L-4->L-5", 0) >= fam_cost, s["sc_id"]


def test_timezone_normalize_chain_dynamic():
    """★ 핵심목표: orchestrator가 c0312→c0313을 실행하고 혼합 tz를 단일 tz로 실제 정규화(silent no-op 0).
    명시 2-c 시퀀스라 boundary 없음, cost=3, meta['tz_normalized']가 default 아닌 명시 True."""
    rec = run_strand(TZ_PAIR, _mixed_tz_df(), {})
    assert rec["actual_c_sequence"] == TZ_PAIR
    assert rec["boundary_at"] is None
    assert rec["total_cost"] == 3
    out = rec["df"]
    # silent no-op 0: 모든 행이 단일 tz(UTC)로 통일됨(무변환이면 KST 잔존 → 실패)
    assert {str(v).split()[-1] for v in out["time_value"]} == {"UTC"}
    assert list(out["time_value"]) == ["00:00 UTC", "00:00 UTC", "03:00 UTC"]
    assert rec["meta"].get("tz_normalized") is True
    record_path(rec, "slice3_timezone_normalize")


def test_timezone_actual_is_best_prefix():
    """actual_c_sequence는 best strand c_sequence의 prefix. post-pair c가 미배선인 strand로 한정하면
    actual==[c0312,c0313]·boundary=그 미배선 c (live REGISTRY 기준 — c0314/c0340 배선형제 내성)."""
    subset = [s for s in TZ
              if s["c_sequence"][:2] == TZ_PAIR and s["c_sequence"][2:3]
              and s["c_sequence"][2] not in REGISTRY][:25]
    assert subset, "post-pair 미배선 strand 부재"
    for s in subset:
        rec = run_strand(s["c_sequence"], _mixed_tz_df(), {})
        n = len(rec["actual_c_sequence"])
        assert rec["actual_c_sequence"] == s["c_sequence"][:n], s["sc_id"]
        assert rec["actual_c_sequence"] == TZ_PAIR, s["sc_id"]
        assert rec["boundary_at"] == s["c_sequence"][2], s["sc_id"]


def test_d_s1_timezone_cut_vertex_negative():
    """★ D-S1: detection(c0312) 없이 c0313(transform) dispatch → RuntimeError (cut-vertex 증명;
    tz_issues가 meta에 있어도 c0312_ran 부재면 거부 — gate는 감지 '실행'이지 산출물 존재가 아님)."""
    with pytest.raises(RuntimeError):
        dispatch("c0313", _mixed_tz_df(), {"tz_issues": {"has_mixed_tz": True}})
