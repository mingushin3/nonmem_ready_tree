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
from src.c_units.c0393_classify_placebo_subject import classify_placebo_subject

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


# ===== Phase 5 · Slice 4 — COVARIATE_LAYOUT family (c0380 DETECT + c0381 CLASSIFY; no Q)
#       + 기구현 자산 c0121 PIVOT 활성화 (c0207 A7 axis 경유; GAP-16/21 종결) =====

COV_MESS = [s for s in STRANDS if "c0380" in s["c_sequence"]]
PIV = [s for s in STRANDS if "c0121" in s["c_sequence"]]
COV_PAIR = ["c0380", "c0381"]
ACTIVATION = ["c0380", "c0381", "c0207", "c0121"]


def _wide_cov_df():
    """wide 공변량(WT_V1,WT_V2) — c0380이 'wide' 감지 → c0121이 long으로 실제 pivot해야 활성화 증명."""
    return pd.DataFrame({"ID": [1, 2], "WT_V1": [70, 55], "WT_V2": [68, 54]})


def test_covariate_strand_count():
    """COVARIATE_LAYOUT mess(c0380)를 지나는 strand 534개, 그중 wide pivot(c0121) 6개."""
    assert len(COV_MESS) == 534
    assert len(PIV) == 6


def test_covariate_detection_precedes_fix_adjacent():
    """D-S1+D-S2: 모든 534 strand에서 c0380이 c0381 직전(인접, canonical order)."""
    for s in COV_MESS:
        seq = s["c_sequence"]
        assert "c0381" in seq, s["sc_id"]
        assert seq.index("c0380") == seq.index("c0381") - 1, s["sc_id"]


def test_covariate_family_cost_within_breakdown():
    """family 한계비용(1+3=4)이 strand의 L-4->L-5 cost_breakdown에 포함된다."""
    fam_cost = COST["c0380"] + COST["c0381"]
    assert fam_cost == 4
    for s in COV_MESS:
        assert s["cost_breakdown"].get("L-4->L-5", 0) >= fam_cost, s["sc_id"]


def test_covariate_classify_chain_dynamic():
    """★ orchestrator가 c0380→c0381을 실행: wide 감지 + 분류 flag 명시 설정(silent no-op 0).
    명시 2-c 시퀀스라 boundary 없음, cost=4, meta['cov_layout_classified']가 default(False) 아닌 True."""
    rec = run_strand(COV_PAIR, _wide_cov_df(), {})
    assert rec["actual_c_sequence"] == COV_PAIR
    assert rec["boundary_at"] is None
    assert rec["total_cost"] == 4
    assert rec["meta"].get("cov_layout") == "wide"
    assert rec["meta"].get("cov_layout_classified") is True


def test_c0121_activation_chain_dynamic():
    """★★ 전략 목표·GAP-16 종결: c0380이 생산한 cov_layout='wide'로 기구현 c0121이 실제 wide→long
    pivot을 수행함을 orchestrator로 증명(c0207 A7 axis 경유). 휴면 자산(분기키 입력 부재) 활성화."""
    rec = run_strand(ACTIVATION, _wide_cov_df(), {"covariate_state": "time-varying"})
    assert rec["actual_c_sequence"] == ACTIVATION
    assert rec["boundary_at"] is None
    assert rec["total_cost"] == 11  # 1+3+3+4
    # 분기키 cov_layout은 c0380(≠c0207)이 생산 — GAP-16 실효 detection.
    assert rec["meta"].get("cov_layout") == "wide"
    assert rec["meta"].get("a7_state") == "TIME-VARYING"
    out = rec["df"]
    # 실제 pivot: wide(WT_V1,WT_V2) → long(visit 컬럼 + WT 값 컬럼), 행수=subjects×visits=4, 비결측 보존.
    assert "visit" in out.columns and "WT" in out.columns
    assert len(out) == 4
    assert set(out["visit"]) == {"V1", "V2"}
    assert sorted(out["WT"].tolist()) == [54, 55, 68, 70]
    record_path(rec, "slice4_covariate_activation")


def test_d_s1_covariate_cut_vertex_negative():
    """★ D-S1: detection(c0207) 없이 c0121(transform) dispatch → RuntimeError (활성화 chain cut-vertex;
    cov_layout가 meta에 있어도 c0207_ran 부재면 거부 — gate는 axis classifier '실행' 보장)."""
    with pytest.raises(RuntimeError):
        dispatch("c0121", _wide_cov_df(), {"cov_layout": "wide"})


# ===== Phase 5 · Slice 5 — PLACEBO_SUBJECT family (c0392 DETECT + c0393 CLASSIFY; no Q)
#       자기완결: 하류 transform/활성화 없음(mess_catalog M103–105). slice 4와 동형이나 더 단순 =====

PBO_MESS = [s for s in STRANDS if "c0392" in s["c_sequence"]]
PBO_PAIR = ["c0392", "c0393"]


def _placebo_df():
    """AMT=0 위약 피험자(2) + 정상 dose — c0392가 has_placebo=True 감지 → c0393이 [2] 분류."""
    return pd.DataFrame({"subject_id": [1, 2, 3], "dose_amount": [100, 0, 100]})


def test_placebo_strand_count():
    """PLACEBO_SUBJECT mess(c0392)를 지나는 strand 543개, c0393도 동수(쌍 공출현)."""
    assert len(PBO_MESS) == 543
    assert len([s for s in STRANDS if "c0393" in s["c_sequence"]]) == 543


def test_placebo_detection_precedes_fix_adjacent():
    """D-S1+D-S2: 모든 543 strand에서 c0392가 c0393 직전(인접, canonical order)."""
    for s in PBO_MESS:
        seq = s["c_sequence"]
        assert "c0393" in seq, s["sc_id"]
        assert seq.index("c0392") == seq.index("c0393") - 1, s["sc_id"]


def test_placebo_family_cost_within_breakdown():
    """family 한계비용(1+3=4)이 strand의 L-4->L-5 cost_breakdown에 포함된다."""
    fam_cost = COST["c0392"] + COST["c0393"]
    assert fam_cost == 4
    for s in PBO_MESS:
        assert s["cost_breakdown"].get("L-4->L-5", 0) >= fam_cost, s["sc_id"]


def test_placebo_classify_chain_dynamic():
    """★ orchestrator가 c0392→c0393을 실행: AMT=0 감지(has_placebo=True) + 위약 피험자 명시 산출
    (placebo_subjects=[2], silent [] no-op 0). 명시 2-c 시퀀스라 boundary 없음, cost=4."""
    rec = run_strand(PBO_PAIR, _placebo_df(), {})
    assert rec["actual_c_sequence"] == PBO_PAIR
    assert rec["boundary_at"] is None
    assert rec["total_cost"] == 4
    assert rec["meta"].get("has_placebo") is True
    assert rec["meta"].get("placebo_subjects") == [2]
    record_path(rec, "slice5_placebo")


def test_d_s1_placebo_artifact_gate_negative():
    """★ artifact-guard(GAP-27 동형): c0392 산출 has_placebo 없이 c0393 직접 실행 → success=False,
    placebo_subjects 미설정. c0393은 detect라 orchestrator D-S1 gate(transform/route 대상) 비대상 —
    impl이 has_placebo artifact를 직접 guard해 silent 통과 차단(slice 4 c0121 transform-gate RuntimeError와 대조)."""
    meta = {}
    result = classify_placebo_subject(_placebo_df(), meta)
    assert result["success"] is False
    assert result["route_to_q"] is None
    assert meta.get("placebo_subjects") is None
