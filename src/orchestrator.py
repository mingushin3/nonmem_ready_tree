"""Phase 5 orchestrator — slice-scoped (DECISION-D2 family interleave).

입력 strand의 c_sequence를 registry 통해 순차 dispatch한다. registry에 배선된 c만 실행하고,
없는 c_id를 만나면 SliceBoundary(NotImplementedError)를 던져 슬라이스 경계를 명시한다
(PROMPTS L298). 영구 stub 금지 — 미구현 c는 진짜로 미구현이다.
slice 1 = MERGED_CELL(c0340/c0341). slice 2 = TIME family(축 detect c0203 + verify c0213
+ ROUTE c0251 + 하류 mess c0310/c0311/c0314/c0315). slice 3 = TIMEZONE(c0312/c0313, TIME mess
블록 마무리; can_route_to_q=[] → no Q). slice 4 = COVARIATE_LAYOUT(c0380/c0381 + 기구현 c0121 PIVOT
활성화, GAP-16 종결). slice 5 = PLACEBO_SUBJECT(c0392/c0393, 자기완결·하류 transform 없음; no Q).

D-S1 (detection-mandatory): transform·route c의 requires_detection_by가 가리키는 DETECT/VERIFY c가
먼저 실행(meta에 '{req}_ran' 기록)되지 않으면 dispatch가 거부한다(cut-vertex). 즉 runtime은
mess_profile을 모른 채 DETECT 결과로만 fix-c/route-c에 도달한다.

terminal 도출: ROUTE c가 a3_state fail → Q-terminal(QUARANTINE + q_code)을 도출하면
run_strand가 거기서 종료한다(D-S4 conditional routing의 strand-내 실현; cost는
strands.json 정합으로 Σc.cost만 누적, Q.routing_cost 비가산). ROUTE 없는 경로의 terminal은
하류 c 구현 후로 보류(None) — 날조 금지.
"""

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.c_units.c0340_detect_merged_cell import detect_merged_cell
from src.c_units.c0341_propagate_merged_cell import propagate_merged_cell
# slice 2: TIME family routing chain (축 detect/verify + ROUTE)
from src.c_units.c0203_detect_time_format import detect_time_format
from src.c_units.c0213_verify_time_anchor import verify_time_anchor
from src.c_units.c0251_route_time_format import route_time_format
# slice 2: TIME mess normalization (L-4->L-5 detect+convert)
from src.c_units.c0310_detect_time_format import detect_time_format_mess
from src.c_units.c0311_convert_time_format import convert_time_format
from src.c_units.c0314_detect_time_anchor import detect_time_anchor
from src.c_units.c0315_convert_time_anchor import convert_time_anchor
# slice 3: TIMEZONE mess normalization (L-4->L-5 detect+normalize) — TIME mess 블록 마무리
from src.c_units.c0312_detect_timezone import detect_timezone
from src.c_units.c0313_normalize_timezone import normalize_timezone
# slice 4: COVARIATE_LAYOUT mess(L-4->L-5 detect+classify) + 기구현 자산 c0121 활성화(GAP-16 종결)
from src.c_units.c0380_detect_covariate_layout import detect_covariate_layout
from src.c_units.c0381_classify_covariate_layout import classify_covariate_layout_mess
from src.c_units.c0207_classify_covariate_layout import classify_covariate_layout
from src.c_units.c0121_pivot_covariate_layout import pivot_covariate_layout
# slice 5: PLACEBO_SUBJECT mess(L-4->L-5 detect+classify) — 자기완결(하류 transform·활성화 없음)
from src.c_units.c0392_detect_placebo_subject import detect_placebo_subject
from src.c_units.c0393_classify_placebo_subject import classify_placebo_subject

_CUNITS_PATH = PROJECT_ROOT / "spec" / "c_units.json"
_CUNITS = json.loads(_CUNITS_PATH.read_text(encoding="utf-8"))
COST = {c["c_id"]: c["cost"] for c in _CUNITS}
REQUIRES_DETECTION = {c["c_id"]: c.get("requires_detection_by") for c in _CUNITS}

# registry: 구현·배선된 c만. 이후 슬라이스가 확장한다(stub 금지).
REGISTRY = {
    # slice 1 — MERGED_CELL
    "c0340": ("detect", detect_merged_cell),
    "c0341": ("transform", propagate_merged_cell),
    # slice 2 — TIME: 축 detect(c0203, 기구현) + verify(c0213) + ROUTE(c0251)
    "c0203": ("detect", detect_time_format),
    "c0213": ("verify", verify_time_anchor),
    "c0251": ("route", route_time_format),
    # slice 2 — TIME mess 정규화(L-4->L-5): detect+convert 쌍 (time_value 생산 chain, GAP-18)
    "c0310": ("detect", detect_time_format_mess),
    "c0311": ("transform", convert_time_format),
    "c0314": ("detect", detect_time_anchor),
    "c0315": ("transform", convert_time_anchor),
    # slice 3 — TIMEZONE 정규화(L-4->L-5): detect+normalize 쌍 (D-S1: c0313 reqdet=c0312, 자동 gate)
    "c0312": ("detect", detect_timezone),
    "c0313": ("transform", normalize_timezone),
    # slice 4 — COVARIATE_LAYOUT: mess detect+classify(c0380/c0381) + 활성화 chain(c0207 A7 axis → c0121 PIVOT)
    # c0381은 detect 등록(D-S1 orchestrator gate는 transform/route 대상) — c0380 의존은 impl artifact-guard(GAP-27).
    # c0121(transform, reqdet=c0207)는 c0207_ran D-S1 gate 자동; c0380 산출 cov_layout='wide'로 실제 pivot(GAP-16 종결).
    "c0380": ("detect", detect_covariate_layout),
    "c0381": ("detect", classify_covariate_layout_mess),
    "c0207": ("detect", classify_covariate_layout),
    "c0121": ("transform", pivot_covariate_layout),
    # slice 5 — PLACEBO_SUBJECT: mess detect+classify(c0392/c0393). can_route_to_q=[] → no Q.
    # 자기완결(하류 transform/활성화 없음, mess_catalog M103–105). c0393은 detect 등록(D-S1 orchestrator
    # gate는 transform/route 대상) — c0392 의존(has_placebo)은 impl artifact-guard(GAP-27 동형, c0381 선례).
    "c0392": ("detect", detect_placebo_subject),
    "c0393": ("detect", classify_placebo_subject),
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
    # D-S1: transform·route는 대응 DETECT/VERIFY 선행 필수(cut-vertex).
    if kind in ("transform", "route") and req is not None and not meta.get(f"{req}_ran"):
        raise RuntimeError(f"D-S1 위반: {c_id}가 detection {req} 이전에 호출됨")
    result = fn(df, meta)
    meta[f"{c_id}_ran"] = True
    return result


def run_strand(c_sequence, df, meta=None, stop_at_boundary=True):
    """strand의 c_sequence를 dispatch. 구현된 prefix를 실행하고, ROUTE c가 Q-terminal을
    도출하면 거기서 종료, 미구현 c(경계)에서도 멈춘다."""
    meta = {} if meta is None else meta
    df_cur = df
    actual = []
    cost = 0
    boundary_at = None
    terminal = None
    q_code = None
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
        # ROUTE c가 terminal(QUARANTINE/INVALID)을 도출하면 그 지점에서 strand 종료(D-S4).
        # detect/verify/transform 결과엔 'terminal' 키가 없어 통과한다(날조 금지).
        if isinstance(result, dict) and result.get("terminal") is not None:
            terminal = result["terminal"]
            q_code = result.get("q_code")
            break
    return {
        "actual_c_sequence": actual,
        "total_cost": cost,
        "terminal": terminal,
        "q_code": q_code,
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
        "q_code": record.get("q_code"),
        "boundary_at": record["boundary_at"],
    }
    path.write_text(json.dumps(serializable, ensure_ascii=False, indent=2), encoding="utf-8")
    return path
