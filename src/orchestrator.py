"""Phase 5 orchestrator — minimal, slice-scoped (DECISION-D2 family interleave).

입력 strand의 c_sequence를 registry 통해 순차 dispatch한다. 이 슬라이스(slice 1)는
MERGED_CELL family(c0340 DETECT + c0341 PROPAGATE)만 구현되어 있으므로, registry에 없는
c_id를 만나면 SliceBoundary(NotImplementedError)를 던져 슬라이스 경계를 명시한다
(PROMPTS L298). 영구 stub 금지 — 미구현 c는 진짜로 미구현이다.

D-S1 (detection-mandatory): transform c의 requires_detection_by가 가리키는 DETECT/VERIFY c가
먼저 실행(meta에 '{req}_ran' 기록)되지 않으면 dispatch가 거부한다(cut-vertex). 즉 runtime은
mess_profile을 모른 채 DETECT 결과로만 fix-c에 도달한다.

terminal 도출은 하류 c들이 모두 구현된 뒤로 미룬다(이 슬라이스에서는 None) — 날조 금지.
"""

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.c_units.c0340_detect_merged_cell import detect_merged_cell
from src.c_units.c0341_propagate_merged_cell import propagate_merged_cell

_CUNITS_PATH = PROJECT_ROOT / "spec" / "c_units.json"
_CUNITS = json.loads(_CUNITS_PATH.read_text(encoding="utf-8"))
COST = {c["c_id"]: c["cost"] for c in _CUNITS}
REQUIRES_DETECTION = {c["c_id"]: c.get("requires_detection_by") for c in _CUNITS}

# slice 1 registry: MERGED_CELL family만. 이후 슬라이스가 확장한다(stub 금지).
REGISTRY = {
    "c0340": ("detect", detect_merged_cell),
    "c0341": ("transform", propagate_merged_cell),
}


class SliceBoundary(NotImplementedError):
    """registry에 없는(=이 슬라이스 미구현) c 호출 — 슬라이스 경계 표식."""


def dispatch(c_id: str, df, meta: dict):
    """단일 c 실행. 미구현이면 SliceBoundary, D-S1 위반이면 RuntimeError."""
    if c_id not in COST:
        raise SliceBoundary(f"{c_id}: c_units.json에 없음")
    if c_id not in REGISTRY:
        raise SliceBoundary(f"{c_id}: 이 슬라이스에서 미구현 (slice boundary)")
    kind, fn = REGISTRY[c_id]
    req = REQUIRES_DETECTION.get(c_id)
    if kind == "transform" and req is not None and not meta.get(f"{req}_ran"):
        raise RuntimeError(f"D-S1 위반: {c_id}가 detection {req} 이전에 호출됨")
    result = fn(df, meta)
    meta[f"{c_id}_ran"] = True
    return result


def run_strand(c_sequence, df, meta=None, stop_at_boundary=True):
    """strand의 c_sequence를 dispatch. 구현된 prefix를 실행하고 경계에서 멈춘다."""
    meta = {} if meta is None else meta
    df_cur = df
    actual = []
    cost = 0
    boundary_at = None
    for c_id in c_sequence:
        try:
            result = dispatch(c_id, df_cur, meta)
        except SliceBoundary:
            boundary_at = c_id
            if stop_at_boundary:
                break
            raise
        actual.append(c_id)
        cost += COST[c_id]
        if isinstance(result, dict) and result.get("df") is not None:
            df_cur = result["df"]
    return {
        "actual_c_sequence": actual,
        "total_cost": cost,
        "terminal": None,        # 하류 미구현 — 도출 보류(날조 금지)
        "boundary_at": boundary_at,
        "df": df_cur,
        "meta": meta,
    }


def record_path(record: dict, sc_id: str) -> Path:
    """슬라이스에서 실제 실행한 sc의 경로 기록 (canonical layout: fixtures/actual/)."""
    out_dir = PROJECT_ROOT / "fixtures" / "actual"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{sc_id}_path.json"
    serializable = {
        "sc_id": sc_id,
        "actual_c_sequence": record["actual_c_sequence"],
        "total_cost": record["total_cost"],
        "terminal": record["terminal"],
        "boundary_at": record["boundary_at"],
    }
    path.write_text(json.dumps(serializable, ensure_ascii=False, indent=2), encoding="utf-8")
    return path
