"""Phase 5 · slice 1 — skeleton (D-S3/D-S4) verification for MERGED_CELL.

D-S3: §6 mess-normalization은 N0–N7 backbone의 앞단 전처리(universe_sm §2/§6, line 33:
"Mess Catalog는 그 앞단에 붙는 normalization 전처리"). 따라서 모든 MERGED_CELL strand에서
L-4->L-5 mess c들이 backbone(비 L-4->L-5) c보다 앞에 온다 — 골격 무모순.
D-S4: 이 family는 Q-code를 트리거하지 않으므로 conditional Q-edge/고립 Q-terminal 무기여.
"""

import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
STRANDS = json.loads((PROJECT_ROOT / "spec" / "strands.json").read_text(encoding="utf-8"))
CUNITS = {c["c_id"]: c for c in
          json.loads((PROJECT_ROOT / "spec" / "c_units.json").read_text(encoding="utf-8"))}

MERGED = [s for s in STRANDS if "c0341" in s["c_sequence"]]


def test_mess_normalization_precedes_backbone():
    """D-S3: 모든 549 strand에서 마지막 L-4->L-5 c index < 첫 비-L-4->L-5 c index."""
    for s in MERGED:
        seq = s["c_sequence"]
        mess_idx = [i for i, c in enumerate(seq) if CUNITS[c]["layer_pair"] == "L-4->L-5"]
        backbone_idx = [i for i, c in enumerate(seq) if CUNITS[c]["layer_pair"] != "L-4->L-5"]
        assert mess_idx, s["sc_id"]
        if backbone_idx:
            assert max(mess_idx) < min(backbone_idx), s["sc_id"]


def test_family_in_mess_stage():
    """c0340/c0341은 L-4->L-5 (mess normalization 전처리 stage)."""
    assert CUNITS["c0340"]["layer_pair"] == "L-4->L-5"
    assert CUNITS["c0341"]["layer_pair"] == "L-4->L-5"


def test_family_introduces_no_q_edge():
    """D-S4: MERGED_CELL family는 Q-code 트리거 없음 → 고립 Q-terminal 무기여."""
    assert CUNITS["c0340"]["can_route_to_q"] == []
    assert CUNITS["c0341"]["can_route_to_q"] == []
    vv = CUNITS["c0340"].get("verify_visualization") or {}
    assert vv.get("fail_route_to") is None


# ===== Phase 5 · Slice 2 — TIME family skeleton (D-S3/D-S4) =====

TIME_MESS = ["c0310", "c0311", "c0314", "c0315"]
TIME_STRANDS = [s for s in STRANDS if any(c in s["c_sequence"] for c in TIME_MESS)]
TIME_Q = [s for s in STRANDS if s.get("q_code") in ("Q02", "Q12")]


def test_time_mess_precedes_backbone():
    """D-S3: TIME mess c(L-4->L-5)는 모든 TIME strand에서 backbone(비 L-4->L-5)보다 앞에 온다."""
    for s in TIME_STRANDS:
        seq = s["c_sequence"]
        mess_idx = [i for i, c in enumerate(seq) if CUNITS[c]["layer_pair"] == "L-4->L-5"]
        backbone_idx = [i for i, c in enumerate(seq) if CUNITS[c]["layer_pair"] != "L-4->L-5"]
        assert mess_idx, s["sc_id"]
        if backbone_idx:
            assert max(mess_idx) < min(backbone_idx), s["sc_id"]


def test_time_c_layer_assignment():
    """TIME mess(c0310/c0311/c0314/c0315)=L-4->L-5; 축(c0203/c0213/c0251)=L-3->L-4."""
    for c in TIME_MESS:
        assert CUNITS[c]["layer_pair"] == "L-4->L-5", c
    for c in ["c0203", "c0213", "c0251"]:
        assert CUNITS[c]["layer_pair"] == "L-3->L-4", c


def test_time_q_terminals_not_isolated():
    """★ D-S4(슬라이스1의 역): c0251.can_route_to_q=[Q02,Q12], 둘 다 ≥1 strand로 도달·c0251로 종착 → 고립 Q-terminal 0."""
    assert CUNITS["c0251"]["can_route_to_q"] == ["Q02", "Q12"]
    reached = {s["q_code"] for s in TIME_Q}
    assert {"Q02", "Q12"} <= reached
    assert all(s["c_sequence"][-1] == "c0251" for s in TIME_Q)


def test_time_convert_q_edge_targets_reachable():
    """D-S4 조기보증: c0311/c0315 can_route_to_q=[Q02] 타깃 Q02 도달가능(Phase 7 conditional-edge 고립 방지)."""
    for c in ["c0311", "c0315"]:
        assert CUNITS[c]["can_route_to_q"] == ["Q02"]
    assert any(s.get("q_code") == "Q02" for s in STRANDS)


# ===== Phase 5 · Slice 3 — TIMEZONE family skeleton (D-S3/D-S4) =====

TZ_MESS = ["c0312", "c0313"]
TZ_STRANDS = [s for s in STRANDS if "c0313" in s["c_sequence"]]


def test_timezone_mess_precedes_backbone():
    """D-S3: 모든 532 strand에서 마지막 L-4->L-5 c index < 첫 비-L-4->L-5(backbone) c index."""
    for s in TZ_STRANDS:
        seq = s["c_sequence"]
        mess_idx = [i for i, c in enumerate(seq) if CUNITS[c]["layer_pair"] == "L-4->L-5"]
        backbone_idx = [i for i, c in enumerate(seq) if CUNITS[c]["layer_pair"] != "L-4->L-5"]
        assert mess_idx, s["sc_id"]
        if backbone_idx:
            assert max(mess_idx) < min(backbone_idx), s["sc_id"]


def test_timezone_c_layer_assignment():
    """c0312/c0313은 L-4->L-5 (mess normalization 전처리 stage)."""
    for c in TZ_MESS:
        assert CUNITS[c]["layer_pair"] == "L-4->L-5", c


def test_timezone_family_introduces_no_q_edge():
    """D-S4: TIMEZONE family는 Q-code 트리거 없음(can_route_to_q=[]) → 고립 Q-terminal 무기여."""
    assert CUNITS["c0312"]["can_route_to_q"] == []
    assert CUNITS["c0313"]["can_route_to_q"] == []
    vv = CUNITS["c0312"].get("verify_visualization") or {}
    assert vv.get("fail_route_to") is None
    assert CUNITS["c0313"].get("verify_visualization") is None


# ===== Phase 5 · Slice 4 — COVARIATE_LAYOUT family skeleton (D-S3/D-S4) =====

COV_MESS_C = ["c0380", "c0381"]
COV_STRANDS = [s for s in STRANDS if "c0380" in s["c_sequence"]]


def test_covariate_mess_precedes_backbone():
    """D-S3: 모든 534 strand에서 마지막 L-4->L-5 c index < 첫 비-L-4->L-5(backbone) c index."""
    for s in COV_STRANDS:
        seq = s["c_sequence"]
        mess_idx = [i for i, c in enumerate(seq) if CUNITS[c]["layer_pair"] == "L-4->L-5"]
        backbone_idx = [i for i, c in enumerate(seq) if CUNITS[c]["layer_pair"] != "L-4->L-5"]
        assert mess_idx, s["sc_id"]
        if backbone_idx:
            assert max(mess_idx) < min(backbone_idx), s["sc_id"]


def test_covariate_c_layer_assignment():
    """c0380/c0381은 L-4->L-5(mess 전처리 stage). 활성화 대상 c0121은 L-2->L-3 backbone(전이 위반 아님)."""
    for c in COV_MESS_C:
        assert CUNITS[c]["layer_pair"] == "L-4->L-5", c
    assert CUNITS["c0121"]["layer_pair"] == "L-2->L-3"


def test_covariate_family_introduces_no_q_edge():
    """D-S4: COVARIATE_LAYOUT family는 Q-code 트리거 없음(can_route_to_q=[]) → 고립 Q-terminal 무기여."""
    assert CUNITS["c0380"]["can_route_to_q"] == []
    assert CUNITS["c0381"]["can_route_to_q"] == []
    vv = CUNITS["c0380"].get("verify_visualization") or {}
    assert vv.get("fail_route_to") is None
    assert CUNITS["c0381"].get("verify_visualization") is None


# ===== Phase 5 · Slice 5 — PLACEBO_SUBJECT family skeleton (D-S3/D-S4) =====

PBO_MESS_C = ["c0392", "c0393"]
PBO_STRANDS = [s for s in STRANDS if "c0392" in s["c_sequence"]]


def test_placebo_mess_precedes_backbone():
    """D-S3: 모든 543 strand에서 마지막 L-4->L-5 c index < 첫 비-L-4->L-5(backbone) c index."""
    for s in PBO_STRANDS:
        seq = s["c_sequence"]
        mess_idx = [i for i, c in enumerate(seq) if CUNITS[c]["layer_pair"] == "L-4->L-5"]
        backbone_idx = [i for i, c in enumerate(seq) if CUNITS[c]["layer_pair"] != "L-4->L-5"]
        assert mess_idx, s["sc_id"]
        if backbone_idx:
            assert max(mess_idx) < min(backbone_idx), s["sc_id"]


def test_placebo_c_layer_assignment():
    """c0392/c0393은 L-4->L-5(mess 전처리 stage). 하류 transform/활성화 대상 없음(자기완결)."""
    for c in PBO_MESS_C:
        assert CUNITS[c]["layer_pair"] == "L-4->L-5", c


def test_placebo_family_introduces_no_q_edge():
    """D-S4: PLACEBO_SUBJECT family는 Q-code 트리거 없음(can_route_to_q=[]) → 고립 Q-terminal 무기여."""
    assert CUNITS["c0392"]["can_route_to_q"] == []
    assert CUNITS["c0393"]["can_route_to_q"] == []
    vv = CUNITS["c0392"].get("verify_visualization") or {}
    assert vv.get("fail_route_to") is None
    assert vv.get("pass_route_to") == "c0393"
    assert CUNITS["c0393"].get("verify_visualization") is None
