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
