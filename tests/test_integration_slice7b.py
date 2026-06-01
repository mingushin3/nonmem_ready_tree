"""Phase 5 · slice 7b — 프런티어 특성화 + GAP-29 정규화 회귀가드 (measure-not-fix).

slice 7a는 backbone 23c를 배선해 완주(no SliceBoundary) strand 173개를 처음 만들었다. 7b 발주
전제는 "구현됐는데 미배선인 상류 c를 더 배선해 173→~467로 올린다"였다. **본 모듈은 그 전제가
falsifiable하게 반증됨을 고정한다:**

  - 구현 파일(src/c_units/*.py) = REGISTRY 배선 = **46**. 미배선-구현 c = **0** → wiring 천장 = 173.
  - 467 완주는 상류 column-path **27c**(L-1→L-2 + L-2→L-3 + L-3→L-4)를 *신규 구현*해야 도달한다
    (배선 아님 — spec/c_units.json엔 entry만, src엔 파일 부재). 전체 73 blocking c 구현 시 5000.
  - 따라서 7b는 (D1) GAP-29 시그니처 정규화 + (D2) 프런티어 정밀 측정으로 한정한다(신규 c 0).
    27c 구현 백로그 = issues/column_path_implementation_backlog.md, DECISION-D2 column-path 확장.

★ ①(외부 meta 미주입)·②(D-S4 conditional edge)는 27c 구현으로 해소되지 않는 **별개 결손**이다.
   27c는 완주 *경로*만 연다 — 본 모듈이 ①/② 수치가 7b에서 7a와 **불변**임을 규모 재확인한다.

신규 코드는 본 하네스뿐이며 c-unit 본문·dispatch 로직은 무변경(D1은 8c 시그니처에 meta=None 추가).
"""

import glob
import json
import os
import re
from pathlib import Path

import pandas as pd

from src.orchestrator import REGISTRY, dispatch, run_strand

PROJECT_ROOT = Path(__file__).resolve().parent.parent
STRANDS = json.loads((PROJECT_ROOT / "spec" / "strands.json").read_text(encoding="utf-8"))
CUNITS = {c["c_id"]: c for c in
          json.loads((PROJECT_ROOT / "spec" / "c_units.json").read_text(encoding="utf-8"))}

# 구현된 c = src/c_units/cXXXX_*.py 파일이 존재하는 c_id.
IMPL = {re.match(r"(c\d+)", os.path.basename(f)).group(1)
        for f in glob.glob(str(PROJECT_ROOT / "src" / "c_units" / "c*.py"))}
REG = set(REGISTRY.keys())

# 완주 strand = best-path 모든 c가 배선됨.
COMPLETING = [s for s in STRANDS if all(c in REGISTRY for c in s["c_sequence"])]

# blocking c = strand에 등장하나 미배선. upstream(column-path) vs mess(L-4->L-5) 분해.
BLOCKERS = sorted({c for s in STRANDS for c in s["c_sequence"] if c not in REGISTRY})
UPSTREAM27 = sorted(c for c in BLOCKERS
                    if CUNITS[c]["layer_pair"] in ("L-1->L-2", "L-2->L-3", "L-3->L-4"))
MESS46 = sorted(c for c in BLOCKERS if CUNITS[c]["layer_pair"] == "L-4->L-5")

# D1 정규화 대상 8c — orchestrator가 fn(df,meta)로 호출하는 호출규약과 정합되어야 함.
GAP29_C = ["c0001", "c0010", "c0011", "c0012", "c0014", "c0016", "c0017", "c0018"]

ROUTE_C = {"c0251", "c0253"}


def _complete_if(extra):
    """REGISTRY ∪ extra가 배선된 상태에서 완주 strand 수."""
    full = REG | set(extra)
    return sum(1 for s in STRANDS if all(c in full for c in s["c_sequence"]))


def _neutral_df():
    """7a와 동일한 고정 neutral 입력(축-state 미주입) — ①/② 특성화 동치 비교용."""
    return pd.DataFrame({
        "ID": [1, 1, 2], "TIME": [0, 1, 0], "DV": [0.0, 1.0, 2.0],
        "time_value": [0, 1, 0], "dv_value": [0.1, 0.2, 0.3], "dose": [100.0, None, 200.0],
    })


# ===== 전제 반증: wiring 천장 도달 =====

def test_wiring_ceiling_reached():
    """★ falsifiable: 구현 c 집합 == REGISTRY 배선 집합(46==46) → 미배선-구현 c = 0.
    즉 'wiring만으로 더 열 strand 없음' = 7b 발주 전제(배선) 반증."""
    assert IMPL == REG, IMPL ^ REG
    assert len(REG) == 46
    assert [c for c in IMPL if c not in REG] == []


def test_completing_now_173_post_normalization():
    """GAP-29 정규화 후에도 완주 = 173(7a와 동일) — 정규화가 완주 집합을 바꾸지 않음."""
    assert len(COMPLETING) == 173


# ===== 프런티어: 27 upstream → 467, 73 → 5000 =====

def test_upstream27_yields_467():
    """★ falsifiable: 상류 column-path 27c를 구현+배선하면 완주 = 정확히 467(=7b 목표).
    27c는 L-1→L-2 + L-2→L-3 + L-3→L-4 blocking c 전수."""
    assert len(UPSTREAM27) == 27
    assert _complete_if(UPSTREAM27) == 467


def test_all73_blockers_yield_5000():
    """★ falsifiable: 전체 73 blocking c(27 upstream + 46 mess) 구현+배선 시 완주 = 5000(전수)."""
    assert len(BLOCKERS) == 73
    assert len(MESS46) == 46
    assert _complete_if(BLOCKERS) == 5000


def test_all_blockers_unimplemented():
    """★ 핵심 반증: 73 blocking c는 전부 미구현(src 파일 부재) — '배선'이 아니라 '신규 구현' 대상."""
    assert all(c not in IMPL for c in BLOCKERS), [c for c in BLOCKERS if c in IMPL]


def test_upstream_layer_decomposition():
    """백로그 정합: upstream 27c의 layer_pair 분해 = L-1→L-2 4 + L-2→L-3 12 + L-3→L-4 11."""
    from collections import Counter
    lp = Counter(CUNITS[c]["layer_pair"] for c in UPSTREAM27)
    assert lp == {"L-1->L-2": 4, "L-2->L-3": 12, "L-3->L-4": 11}, dict(lp)


# ===== GAP-29 정규화 회귀가드 =====

def test_gap29_dispatch_callable_no_typeerror():
    """★ GAP-29 RESOLVED 가드: 8c가 orchestrator dispatch(fn(df,meta)) 호출규약으로 호출돼도
    TypeError 0(정규화 전엔 (df)-only라 TypeError). reqdet은 meta에 _ran 주입해 D-S1 충족."""
    df = pd.DataFrame({
        "subject_id": [1, 1, 2], "event_type": ["dose", "obs", "obs"],
        "time_value": [0, 1, 0], "dv_value": [None, 1.0, 2.0],
    })
    for c in GAP29_C:
        rd = CUNITS[c].get("requires_detection_by")
        meta = {f"{rd}_ran": True} if rd else {}
        try:
            dispatch(c, df.copy(), meta)
        except TypeError as e:  # 호출규약 위반만 실패로 본다
            raise AssertionError(f"{c} dispatch raised TypeError (정규화 미적용): {e}")
        except Exception:
            pass  # 로직상 success=False/route 등은 본 가드의 관심사 아님


def test_gap29_backward_compatible_single_arg():
    """후방호환: 8c를 기존 단위테스트처럼 fn(df) 단일인자로 호출해도 정상(meta=None 기본값)."""
    from src.c_units.c0001_verify_column_schema import verify_column_schema
    from src.c_units.c0010_assign_evid import assign_evid
    from src.c_units.c0018_assign_id import assign_id
    df = pd.DataFrame({
        "subject_id": [1, 2], "event_type": ["obs", "obs"],
        "time_value": [0, 1], "dv_value": [1.0, 2.0],
    })
    assert verify_column_schema(df)["pass"] in (True, False)   # df-only 호출 TypeError 없음
    assert assign_evid(df)["success"] in (True, False)
    assert assign_id(df)["success"] in (True, False)


# ===== ①/② 불변: 7b는 ①/②를 바꾸지 않음(27c가 안 건드림) =====

def test_terminal_realization_still_starved_unchanged():
    """★ ① 불변: 완주 173에서 meta 미주입 시 기대-q 실현 여전히 0(7a와 동일).
    27c 구현 백로그는 완주 경로만 열 뿐, ①(외부 meta 주입 규약) 결손은 그대로다."""
    runs = [(s, run_strand(s["c_sequence"], _neutral_df(), {})) for s in COMPLETING]
    realized = [s["sc_id"] for s, rec in runs if s["q_code"] and rec["q_code"] == s["q_code"]]
    assert realized == [], realized


def test_d_s4_runtime_isolated_still_unchanged():
    """★ ② 불변: axis evaluator 종착 strand는 여전히 terminal 미실현(68개, 그중 Q05 via c0201 4개).
    Phase 7 D-S4 conditional-edge 재구성이 흡수할 결손 — 27c와 별개, 7b에서 수치 불변."""
    runs = [(s, run_strand(s["c_sequence"], _neutral_df(), {})) for s in COMPLETING]
    axis_last = [(s, rec) for s, rec in runs if s["c_sequence"][-1] not in ROUTE_C]
    assert len(axis_last) == 68
    assert all(rec["terminal"] is None for s, rec in axis_last)
    q05 = [s for s, _ in axis_last if s["q_code"]]
    assert len(q05) == 4
    assert all(s["q_code"] == "Q05" and s["c_sequence"][-1] == "c0201" for s in q05)
