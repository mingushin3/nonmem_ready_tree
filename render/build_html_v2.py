"""render/build_html_v2.py — index_v2.html: 대학 1학년도 이해하는 '쉬운 설명 뷰' + 파일 진단 마법사.

★ 표현층 전용. 엔진/spec/SSOT 무수정(report-only). 정본 index.html(build_html.py)은 그대로 보존하고,
  본 파일은 별도 산출물 render/index_v2.html만 쓴다. 데이터층(ELES/CUNITS/QINFO/…/LIBS/js)은
  build_html.py를 import해 재사용하고, (1) 색을 진한 앰버(기본 자동경로)+청록(질문 갈림길)로 바꾸고,
  (2) 패널 문구를 쉬운 말 + 코드 배지 + hover 용어집으로 재작성하고, (3) src/adapter 정본을 1:1 미러한
  '내 파일 진단' 마법사를 붙인다.

★ 진단 마법사의 판정 상수(_FILE_PROPERTY/_DATA_DEPENDENT/_CANON_ORDER/_QA_TOKENS)는 src.adapter에서
  직접 import → 빌드 시점에 정본과 동일함이 보장된다(drift 불가). 판정 로직(faithful_tidy 게이트 +
  precondition-gated c-sequence)은 navigator.choose_detect_sequence / xlsx_ingester._classify_shape 를
  그대로 옮긴 것이며, tests/test_render_v2.py가 wizard 판정 == src.adapter.ingest() 임을 검증한다.

색: --hl-single #FFD700→진한 앰버(#E8820C, 실선) · --hl-cond #FFF8B0→청록(#15B4C7, 점선).
    의미(실선=자동 진행 / 점선=질문 Q로 갈리는 갈림길)는 유지하고 색만 교체 → Lock7/index.html 무영향.
"""
import json
import os
import re
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
sys.path.insert(0, _HERE)   # import build_html (sibling)
sys.path.insert(0, _ROOT)   # import src.adapter (repo root)

import build_html as B  # noqa: E402  데이터층 재사용(main 가드 → import 시 index.html 미작성)

# ── 정본 어댑터 상수(live import → drift 불가) ────────────────────────────────
from src.adapter.navigator import _FILE_PROPERTY, _DATA_DEPENDENT, _CANON_ORDER  # noqa: E402
from src.adapter import xlsx_ingester as XI  # noqa: E402  (_QA_TOKENS, _classify_shape priority)
from src.adapter.column_canonicalizer import _SUBJ as _SUBJ_RE  # noqa: E402  (has_subject 판정)


# ═════════════════════════════════════════════════════════════════════════════
# 1. 진단 마법사 — src/adapter 1:1 미러 (WIZARD 상수 + 판정 로직)
# ═════════════════════════════════════════════════════════════════════════════
#
# navigator._precondition_ok(df-present, tidy 케이스)의 컬럼 요구를 데이터로 표현.
#   none           : len(df)>0 (faithful 밴드에선 항상 충족)
#   time           : time_value/TIME 존재 (tidy 시트는 시간 헤더 보장 → canonicalize가 time_value 매핑)
#   dv             : dv_value/DV 존재 (tidy 시트는 농도 헤더 보장)
#   subject+time+dv: 셋 다 (subject 열 유무 = has_subject)
PRECOND = {
    "c0201": "none", "c0210": "none", "c0214": "none", "c0215": "none",
    "c0216": "none", "c0314": "none",
    "c0203": "time", "c0310": "time", "c0312": "time",
    "c0205": "dv", "c0211": "dv", "c0305": "dv",
    "c0212": "subject+time+dv",
}

# honest-stop recipe WU 매핑(recipe_emitter._wu1_qa/_wu1_param_summary/_wu3_pivot/_wu4_join 의 name)
WIZARD_WU = {"qa": "QA-strip", "param": "param-summary-reserve",
             "subject_wide": "pivot-wide-to-long", "dose_bw": "dose-bw-join"}

WIZARD = {
    "file_property_c": list(_FILE_PROPERTY),       # ('c0201','c0210')
    "data_dependent_c": list(_DATA_DEPENDENT),
    "canon_order": list(_CANON_ORDER),
    "qa_tokens": list(XI._QA_TOKENS),
    "shape_priority": ["qa-contaminated", "param-summary", "subject-wide", "tidy-long", "unknown"],
    "precond": dict(PRECOND),
    "wu_map": dict(WIZARD_WU),
    # 사람가독 패턴 설명(브라우저 표시용; 판정에 쓰지 않음)
    "patterns": {
        "tidy": "헤더에 '시간'(time/시간/nominal) 열과 '농도'(conc/DV/농도/observation) 열이 둘 다",
        "subject_wide": "헤더에 개체(subject/animal/개체/동물/ID)류 열이 2개 이상",
        "param_summary": "셀에 'Parameter'와 'Unit'(단위)이 함께 (값은 Mean)",
        "qa": "첫 열에 Standard/DBLK/BLK/QC/Calibration/Blank 등 검량·QA 행",
    },
}


def wizard_verdict_from_answers(a: dict) -> dict:
    """예/아니오 답 → 판정. navigator.choose_detect_sequence 미러(faithful 밴드 컬럼 완비 가정).

    faithful = tidy 시트 존재(ingest: "tidy-long" in shapes). qa/param/subject_wide 는 honest-stop
    '이유'에만 쓰이고 faithful 자체는 막지 않는다(ingest 와 동일 — tidy 시트가 있으면 faithful).
    """
    faithful = bool(a.get("tidy"))
    chosen = set(_FILE_PROPERTY)
    if faithful:
        for c in _DATA_DEPENDENT:
            req = PRECOND[c]
            ok = (req == "none"
                  or req == "time"            # tidy ⇒ 시간 헤더 보장
                  or req == "dv"              # tidy ⇒ 농도 헤더 보장
                  or (req == "subject+time+dv" and bool(a.get("has_subject"))))
            if ok:
                chosen.add(c)
    c_sequence = [c for c in _CANON_ORDER if c in chosen]
    return {
        "faithful_tidy": faithful,
        "entry_node": "N0",
        "c_sequence": c_sequence,
        "honest_stop": (not faithful),
        "stop_at": ("navigable-band-complete" if faithful else "structure-recognition"),
        "gap": (None if faithful else "GAP-37"),
    }


def _answers_from_structure(structure: dict) -> dict:
    """read_workbook_structure 산출 → 마법사 답 벡터(정본 분류기로 도출 — 새 판정 로직 0)."""
    shapes = [s["shape_class"] for s in structure["per_sheet"].values()]
    has_tidy = "tidy-long" in shapes
    has_subject = False
    if has_tidy:
        for s in structure["per_sheet"].values():
            if s["shape_class"] == "tidy-long":
                has_subject = any(_SUBJ_RE.search(h or "") for h in s.get("header_row", []))
                break
    merged = any(s.get("n_merged", 0) for s in structure["per_sheet"].values())
    return {
        "qa": "qa-contaminated" in shapes,
        "param": "param-summary" in shapes,
        "subject_wide": "subject-wide" in shapes,
        "tidy": has_tidy,
        "has_subject": has_subject,
        "multi_or_merged": (structure.get("n_sheets", 1) > 1) or bool(merged),
        "non_ascii": bool(structure.get("non_ascii_present")),
    }


def wizard_verdict_from_structure(structure: dict) -> dict:
    """구조 → 답 → 판정(=ingest 동치 검증용)."""
    return wizard_verdict_from_answers(_answers_from_structure(structure))


# ═════════════════════════════════════════════════════════════════════════════
# 2. 용어집(GLOSSARY) — 코드 집합은 SSOT 파생, 쉬운 말만 큐레이트
# ═════════════════════════════════════════════════════════════════════════════

_PLAIN_AXIS = {
    "A0": "분석 목적 — 무엇을 분석하나(PK·집단PK·PK/PD 등)와 endpoint 종류가 적혀 있나?",
    "A1": "연구 통합 — 한 연구인가, 여러 연구를 합치나(합치면 환자번호 통일 필요)?",
    "A2": "연구 설계 — 평행군·교차·생동성·전임상 등 어떤 구조인가?",
    "A3": "시간 — 사건이 '언제' 일어났는지 정할 수 있나(실제/예정/경과)?",
    "A4": "투약 완전성 — 모든 용량이 적혀 있고 충돌은 없나?",
    "A5": "관측/BLQ — 관측값이 있고, BLQ·LLOQ·ULOQ·반복 처리가 정해져 있나?",
    "A6": "행 분류 — 투약 행과 관측 행을 분명히 나눌 수 있나?",
    "A7": "공변량 — 필요한 공변량이 있고 붙일(연결) 수 있나?",
    "A8": "약물/구획 — 약·대사체가 몇 개이고 구획 번호가 정해졌나?",
    "A9": "결함 복구 — 중복·정렬·인코딩 같은 구조 결함을 고칠 수 있나?",
    "A10": "원본 형식 — 파일이 어떤 형식이고 안정적으로 읽을 수 있나?",
}

_PLAIN_NODE = {
    "N0": "출발 관문 — 분석 목적이 분명하고 endpoint 종류가 적혀 있나?",
    "N1": "개체(사람/동물) 번호를 만들 수 있나?",
    "N2": "사건을 시간순으로 줄세울 수 있나?",
    "N3": "투약 기록을 완성할 수 있나?",
    "N4": "관측 기록을 완성할 수 있나? (관측이 없다고 바로 실패는 아님)",
    "N5": "BLQ·결측·MDV를 처리할 수 있나? (ULOQ 초과 포함)",
    "N6": "공변량을 붙일 수 있나?",
    "N7": "남은 애매함이 기준 이하인가? → 자동/정리/격리 판정",
}

_PLAIN_TERMINAL = {
    "AUTO": "그대로 자동으로 NONMEM-ready 완성",
    "REPAIR": "정해진 정책을 적용해 고치면 ready",
    "QUARANTINE": "데이터는 있으나 결정이 필요 → 사람(스폰서) 답변 대기",
    "UNSUPPORTED": "지금 도구가 다루지 못하는 형식(범위 밖)",
    "INVALID": "핵심 정보가 없어 되살릴 수 없음 → 사용 불가",
}

_PLAIN_KIND = {
    "transform": "변환 — 데이터를 실제로 고치는 작업",
    "detect": "감지 — 문제/패턴이 있는지 찾아냄(고치진 않음)",
    "verify": "검사 — 조건이 맞는지 확인하고 통과/실패 판정",
    "route": "분기 — 막히면 어느 질문/종착으로 보낼지 결정",
}

_PLAIN_LAYER = {
    "L-4->L-5": "가장 바닥 정리 — 글자·인코딩·셀·토큰 정규화(L-5→L-4)",
    "L-3->L-4": "축(A0~A10) 평가 경계 — 잡음 정리 후 갈림길 판단(L-4→L-3)",
    "L-2->L-3": "깔끔한 long 표 만들기 — 시트 합치기·wide→long(L-3→L-2)",
    "L-1->L-2": "NONMEM 핵심 열 부여 — ID/TIME/DV/EVID 등(L-2→L-1)",
}

_PLAIN_Q = {
    "Q01": "BLQ/LLOQ(검출한계) 처리 방법이 안 정해짐 → 방법(M1/M3 등)·LLOQ 값을 정해달라는 질문",
    "Q02": "시간을 실제/예정/경과 중 무엇으로 쓸지, 기준점이 어딘지 안 정해짐",
    "Q03": "집단 PK에서 '회차(occasion)'를 어떻게 나눌지 안 정해짐",
    "Q04": "행이 투약인지 관측인지, 투약-채혈 연결이 애매함",
    "Q05": "여러 연구를 합칠 때 환자번호 충돌 규칙이 없음",
    "Q06": "프로토콜 위반을 어떻게 처리할지 규칙이 없음",
    "Q07": "결측 공변량을 어떻게 채울지 방법이 없음",
    "Q08": "투약 기록 출처 충돌 또는 복원 정책이 없음",
    "Q09": "약물·대사체에 구획(CMT) 번호를 어떻게 줄지 규칙이 없음",
    "Q10": "단위 사전(분자량 MW 포함)이 불완전함",
    "Q11": "분석 목적·endpoint 종류가 충분히 안 적힘",
    "Q12": "시간 기준을 되살릴 수 없음(추가 자료 필요, 또는 사용 불가 수용)",
    "Q13": "외부 공변량 표의 연결키(merge key)가 모호함",
    "Q14": "반복 투약(ADDL/II)과 실제 투약이 충돌, 우선순위 규칙이 없음",
    "Q15A": "데이터 패키지가 불완전(필수 산출물 누락)",
    "Q15B": "정체불명 legacy 표시열의 의미가 문서화 안 됨",
    "Q15C": "실세계 투약 이력 불확실(환자 진술 기반) 미해결",
    "Q15D": "재분석 결과 중 최종본 판정 문서가 없음",
    "Q15X": "어디에도 안 맞는 정체불명 결함(강한 페널티)",
}

# 축별 상태(101개) — 쉬운 말. 코드 집합은 anchors.json(=B.AXIS_STATES) SSOT, 본 dict는 쉬운 말만.
_PLAIN_STATE = {
    # A0 분석 의도
    "A0::AIC-MISSING": "분석 목적이 안 적힘 → 무엇을 분석하는지 먼저 밝혀야 함(Q11)",
    "A0::AIC-PK": "기본 약동학(PK) 분석",
    "A0::AIC-POPPK": "집단 PK(popPK) — '회차(occasion)' 구분 필요",
    "A0::AIC-PKPD": "약물 농도와 효과를 잇는 PK/PD 분석",
    "A0::AIC-ER": "노출(exposure)–반응 분석 — 노출 지표 미리 계산 필요",
    "A0::AIC-DDI": "약물 상호작용(DDI) 분석",
    "A0::AIC-PEDS": "소아 분석 — 용량 재구성 정책 필요",
    "A0::AIC-SPECIAL": "특수집단(신장/간장애 등) 분석",
    "A0::AIC-CUSTOM": "표준에 없는 맞춤 목적 — 정책 문서 필요",
    # A1 연구 통합
    "A1::SINGLE": "연구 하나 — 통합 작업 불필요",
    "A1::MULTI-HOMO": "같은 설계의 여러 연구 — 합치는 규칙 필요(없으면 Q05)",
    "A1::MULTI-HETERO": "설계가 다른 여러 연구 — 합치는 규칙 필요(없으면 Q05)",
    "A1::MULTI-SITE": "같은 연구의 여러 기관 — 환자번호 통일 필요(없으면 Q05)",
    "A1::INTERIM": "중간분석 시점 데이터 — 누적(pooling) 규칙 필요",
    # A2 연구 설계
    "A2::PARALLEL": "평행군 설계(군마다 다른 처치)",
    "A2::SAD-MAD": "단회/반복 용량 증량 시험",
    "A2::CROSSOVER": "교차 설계(한 사람이 여러 처치, 휴약기)",
    "A2::BE": "생물학적 동등성 시험(대조약 vs 시험약)",
    "A2::DDI": "약물 상호작용 시험",
    "A2::FOOD-EFFECT": "음식 영향 시험(공복 vs 식후)",
    "A2::SPECIAL-POP": "특수집단 시험",
    "A2::PEDIATRIC": "소아 시험(체중/체표면적 기반 용량)",
    "A2::TDM-RWD": "치료약물모니터링/실세계데이터(환자 진술 기반 가능)",
    "A2::PRECLINICAL": "전임상(동물) 시험",
    # A3 시간
    "A3::ACTUAL": "실제 측정된 시각(벽시계 시간)",
    "A3::NOMINAL-ONLY": "예정된 시각만 있음(실제 기록 없음)",
    "A3::ACTUAL-PREFERRED": "둘 다 있고 실제 시각을 사용",
    "A3::NOMINAL-PREFERRED": "둘 다 있고 예정 시각을 사용",
    "A3::ELAPSED": "투약 이후 경과시간(상대 시간)",
    "A3::INTERVAL": "구간으로 기록된 시간(예: 2~4시간)",
    "A3::AMBIGUOUS": "시간 해석이 여러 가지로 갈려 애매함 → 사람이 정해야 함(Q02)",
    "A3::UNRECOVERABLE": "시간 정보가 아예 없어 되살릴 수 없음 → 진행 불가(Q12/INVALID)",
    # A4 투약 완전성
    "A4::COMPLETE": "모든 투약이 완비됨 → 자동 진행",
    "A4::WEIGHT-BASED": "체중당 용량(mg/kg) — 재구성 정책 필요",
    "A4::BSA-BASED": "체표면적당 용량(mg/m²) — 정책 필요",
    "A4::PLANNED-FALLBACK": "실제가 없으면 예정 용량 사용",
    "A4::ADDL-II": "등간격 반복 투약(ADDL/II로 압축)",
    "A4::ADDL-ACTUAL-CONFLICT": "반복 투약 정보와 실제 투약이 어긋남 → 우선순위 결정 필요(Q14)",
    "A4::TITRATION-ADAPTIVE": "용량 조절(적정) — 정책 없으면 질문(Q08)",
    "A4::LOADING-MAINTENANCE": "부하+유지 용량 — 정책 없으면 질문(Q08)",
    "A4::INFUSION-STOP-RESTART": "정맥주입 중단/재개·속도변경 — 정책 없으면 질문(Q04)",
    "A4::PARTIAL-RECOVERY": "일부 투약만 있음 → 나머지 추정·표시",
    "A4::COMBINATION": "여러 약 병용 — 경로/구획 정책 필요",
    "A4::MISSING-NO-POLICY": "투약 기록 없고 복원 규칙도 없음 → 질문(Q08)",
    "A4::UNRECOVERABLE": "필수 투약 정보가 없어 되살릴 수 없음 → 진행 불가",
    # A5 관측/BLQ
    "A5::CLEAN": "관측값 깨끗함(BLQ 없음) → 자동 진행",
    "A5::BLQ-FLAGGED": "BLQ가 플래그로 표시 + 정책 있음 → 정리 가능",
    "A5::BLQ-TEXT": "BLQ가 글자로(<0.1, 'BLQ') → 해석·정규화",
    "A5::BLQ-ZERO": "BLQ가 0으로 표시 → 진짜 0과 구분 필요",
    "A5::MULTI-ANALYTE": "여러 분석물질(모약물·대사체) — 구획 정책 필요",
    "A5::LLOQ-CHANGED": "정량하한(LLOQ)이 중간에 바뀜 → 표시·정리",
    "A5::MISSING-MDV1": "관측 결측 → MDV=1로 표시(자동)",
    "A5::BIOANALYTICAL-FINAL-FLAG-MISSING": "여러 분석 결과 중 최종본 표시 없음 → 질문(Q15D)",
    "A5::ABOVE-ULOQ": "정량상한(ULOQ) 초과 + 정책 있음 → 정리 가능",
    "A5::ABOVE-ULOQ-NO-POLICY": "ULOQ 초과인데 처리 정책 없음 → 질문(Q01)",
    "A5::REPLICATE-SAME-TIME": "같은 시점 반복 측정 + 정책 있음 → 정리(평균/대표/모두)",
    "A5::REPLICATE-NO-POLICY": "반복 측정인데 처리 정책 없음 → 질문(Q01)",
    "A5::BLQ-NO-POLICY": "BLQ 있는데 처리 방법(M1/M3…) 없음 → 질문(Q01)",
    "A5::LLOQ-MISSING": "BLQ 있는데 LLOQ 값이 없음 → 질문(Q01)",
    "A5::ABSENT": "관측값이 아예 없음 → 진행 불가(INVALID)",
    # A6 행 분류
    "A6::SEPARABLE": "투약 행과 관측 행이 시각으로 구분됨 → 자동",
    "A6::SAME-TIME-RESOLVABLE": "같은 시각이지만 투약→관측 순서가 정해짐 → 정리 가능",
    "A6::COVARIATE-CHANGE": "공변량 변경 행(EVID=2) 있음 → 표시",
    "A6::RESET-NEEDED": "구획 초기화 행 필요(휴약 등) → 표시",
    "A6::URINE-INTERVAL": "소변 수집 구간(0~4h 등) → 구간 표시",
    "A6::AMBIGUOUS": "행이 투약인지 관측인지 애매함 → 질문(Q04)",
    # A7 공변량
    "A7::NONE-REQUIRED": "공변량 불필요 → 자동",
    "A7::BASELINE-CLEAN": "기저 공변량 완비 → 자동(첫 값 사용)",
    "A7::BASELINE-IMPUTABLE": "기저 공변량 결측 + 보충 정책 있음 → 정리",
    "A7::TIME-VARYING": "시간에 따라 변하는 공변량 → 시점 맞춰 정리",
    "A7::EXTERNAL-JOIN": "별도 표의 공변량 + 연결키 있음 → 합치기",
    "A7::PEDIATRIC-MATURATION": "소아 성숙(나이) 함수 적용 → 정리",
    "A7::KEY-MISSING": "외부 공변량 표의 연결키가 모호 → 질문(Q13)",
    "A7::POLICY-MISSING": "공변량 결측 처리 방법이 없음 → 질문(Q07)",
    # A8 약물/구획
    "A8::SINGLE-DRUG": "약 하나, 구획 하나 → 자동",
    "A8::MULTI-CMT-DEFINED": "여러 약/대사체 + 구획 규칙 있음 → 정리",
    "A8::DDI-VICTIM-ONLY": "상호작용에서 영향 받는 약만 → 정리",
    "A8::DDI-VICTIM-PERPETRATOR": "영향 받고+주는 약 둘 다 → 구획 분리",
    "A8::METABOLITE-DEFINED": "모약물+대사체 별도 구획 → 정리",
    "A8::CMT-POLICY-MISSING": "구획 번호 배정 규칙이 없음 → 질문(Q09)",
    # A9 결함 복구
    "A9::CLEAN": "구조/인코딩 결함 없음 → 자동",
    "A9::DUPLICATE-EXACT": "완전 중복 행 → 중복 제거",
    "A9::UNSORTED": "정렬 안 됨(ID·시간순 아님) → 정렬",
    "A9::COLUMN-SYNONYM": "같은 뜻 열이 여러 개 → 표준 하나 선택",
    "A9::UNIT-CONVERSION": "단위 불일치(mg vs µg) → 표준화",
    "A9::ENCODING-FIX": "문자 인코딩 문제(cp949 등) → UTF-8 변환",
    "A9::PRE-DOSE-SAMPLE": "투약 전 채취(시간<0/'PRE') → 정리",
    "A9::PLANNED-VS-ACTUAL": "예정값·실제값 둘 다 + 선택 정책 → 정리",
    "A9::PROTOCOL-DEVIATION": "프로토콜 위반 기록 있음 → 표시(정책 없으면 Q06)",
    "A9::REANALYSIS-FINAL-DEFINED": "재분석 + 최종본 표시됨 → 정리",
    "A9::REANALYSIS-FINAL-MISSING": "재분석인데 최종본 표시 없음 → 질문(Q15D)",
    "A9::PROTOCOL-DEVIATION-NO-POLICY": "위반 있는데 처리 규칙이 없음 → 질문(Q06)",
    "A9::IRRECONCILABLE": "데이터 무결성 깨짐(해결 불가) → 진행 불가",
    # A10 원본 형식
    "A10::SDTM-ADaM": "CDISC 표준(SDTM/ADaM) 형식 → 자동 파싱",
    "A10::EDC-STRUCTURED": "임상 EDC 추출본 → 평탄화·표준화",
    "A10::CRO-VENDOR": "CRO 제공 형식(벤더별) → 규격대로 파싱",
    "A10::FLAT-TABULAR": "단순 평면 표(깔끔한 CSV/Excel) → 약간 정리",
    "A10::LEGACY-NM": "기존 NONMEM 데이터셋(이미 포맷됨) → 검증",
    "A10::SEMI-STRUCTURED": "여러 시트/표를 합쳐야 함(투약+관측 시트) → 합치기",
    "A10::NON-TABULAR": "표가 아님(텍스트/PDF/이미지) → 미지원",
    "A10::CORRUPTED": "파일 손상(읽기 불가) → 진행 불가",
}

# 통제 어휘(srp_intent의 VERB/NOUN/MODIFIER) — spec/vocabulary.md 기반 쉬운 말.
_PLAIN_VOCAB = {
    # VERB (13)
    "ASSIGN": "값을 채워 넣기", "VERIFY": "검사하기", "CONVERT": "형식 바꾸기",
    "NORMALIZE": "여러 표기를 하나로 통일", "JOIN": "표 합치기(공통 키로)",
    "SPLIT": "한 열/칸을 여러 개로 나누기", "PIVOT": "wide↔long 모양 바꾸기",
    "FILTER": "조건에 맞는 행에 표시(삭제 아님)", "DETECT": "문제/패턴 찾아내기",
    "PROPAGATE": "값을 옆 행으로 채워 퍼뜨리기", "CLASSIFY": "정해진 범주로 분류",
    "EXTRACT": "글 속에서 값 뽑아내기", "ROUTE": "막히면 어디로 보낼지 결정",
    # MODIFIER (7) + BY
    "BY": "범위 한정:", "WITHIN_ID": "개체(ID) 안에서만", "WITHIN_OCCASION": "회차 안에서만",
    "WITHIN_ANALYTE": "분석물질 안에서만", "ACROSS_SHEET": "시트 경계를 넘어",
    "ACROSS_FILE": "파일 경계를 넘어", "PER_SUBJECT": "개체별로 반복", "PER_VISIT": "방문별로 반복",
    # NOUN — NONMEM_COLUMN (10) + BLQ/LLOQ 부수 열
    "ID": "개체 번호 열", "TIME": "시간 열", "DV": "관측값 열", "MDV": "관측결측 표시 열",
    "EVID": "이벤트 종류 열", "AMT": "투여량 열", "CMT": "구획 번호 열", "RATE": "주입 속도 열",
    "ADDL": "추가 투여 횟수 열", "II": "투여 간격 열",
    "BLQ_FLAG": "BLQ 표시 열(정량하한 미만 여부)", "LLOQ": "정량하한 값 열(LLOQ)",
    # NOUN — MESS_CONCEPT (26)
    "NA_TOKEN": "결측 토큰(NA/빈칸/999 등)", "BLQ_TOKEN": "BLQ 토큰(<LLOQ/ND 등)",
    "TIME_FORMAT": "시간 표기 형식", "TIME_ANCHOR": "시간 기준점", "TIMEZONE": "시간대",
    "ID_DTYPE": "ID 자료형(문자/숫자 혼재)", "ID_LEADING_ZERO": "ID 앞자리 0",
    "MERGED_CELL": "병합 셀", "MULTI_LEVEL_HEADER": "다단 헤더", "TRAILING_BLANK": "꼬리 빈 행",
    "DUPLICATE_ROW": "완전 중복 행", "NATURAL_LANGUAGE_DOSE": "자연어 용량('100mg')",
    "NATURAL_LANGUAGE_TIME": "자연어 시간('30분 후')", "FREETEXT_COMMENT": "자유 텍스트 코멘트",
    "EXCEL_FORMULA": "엑셀 수식 잔존", "EXCEL_DATE_SERIAL": "엑셀 날짜 일련번호",
    "NON_ASCII_DECIMAL": "비표준 소수점/천단위", "LINEBREAK_IN_CELL": "셀 안 줄바꿈",
    "SCIENTIFIC_NOTATION": "과학적 표기(1E+3)", "COVARIATE_LAYOUT": "공변량 배치(wide/long)",
    "PRE_DOSE_CODING": "투약 전 시점 코딩", "PLACEBO_SUBJECT": "위약군 피험자",
    "ABOVE_ULOQ": "ULOQ 초과 관측", "REPLICATE_OBS": "정당한 반복 관측",
    "LEGACY_FLAG_PRESENT": "정체불명 legacy 표시열", "RWD_ADHERENCE_UNRESOLVED": "실세계 투약 불확실",
    # NOUN — DOMAIN_ENTITY (9)
    "DOSE_SHEET": "투약 시트", "COVARIATE_SHEET": "공변량 시트", "ANALYTE_COLUMN": "분석물질(농도) 열",
    "BASELINE_COVARIATE": "기저 공변량", "TIME_VARYING_COVARIATE": "시변 공변량",
    "METABOLITE": "대사체", "PARENT_DRUG": "모약물", "OCCASION": "투여 회차",
    "REGIMEN_DESCRIPTOR": "투여 요법 설명",
    # NOUN — FILE_PROPERTY (6)
    "ENCODING": "문자 인코딩", "FILE_FORMAT": "파일 형식", "SHEET_INVENTORY": "시트 목록",
    "BOM": "BOM(바이트순서표시)", "LINE_ENDING": "줄바꿈 문자", "DELIMITER": "구분자",
    # NOUN — UNIT_PROPERTY (4)
    "UNIT_DECLARATION": "단위 표기", "UNIT_CONSISTENCY": "단위 일관성",
    "UNIT_CANONICAL": "단위 표준형", "MOLAR_MASS": "분자량(MW)",
    # NOUN — SCHEMA_PROPERTY (4)
    "COLUMN_SCHEMA": "열 구조(필수 열 존재·타입)", "ROW_ORDERING": "행 정렬 규칙",
    "ROW_LEVEL_INVARIANT": "행 수준 불변조건", "CROSS_COLUMN_INVARIANT": "열 간 불변조건",
}


def build_glossary():
    state = {}
    for ax, sts in B.AXIS_STATES.items():
        for s in sts:
            state[ax + "::" + s] = _PLAIN_STATE.get(ax + "::" + s)
    return {
        "axis": {ax: _PLAIN_AXIS.get(ax) for ax in B.AXIS_IDS},
        "state": state,
        "node": {n: _PLAIN_NODE.get(n) for n in B.BRANCH_IDS},
        "qcode": {q: _PLAIN_Q.get(q) for q in B.Q_IDS},
        "kind": dict(_PLAIN_KIND),
        "layer": dict(_PLAIN_LAYER),
        "terminal": {t: _PLAIN_TERMINAL.get(t) for t in B.PROC_IDS},
        "vocab": dict(_PLAIN_VOCAB),
    }


GLOSSARY = build_glossary()


# ═════════════════════════════════════════════════════════════════════════════
# 2.5 쉬운 LLM 지시문 + R 골격(EASY) — 파일럿 6개
#     정본 spec/c_units.json을 직접 읽어(무수정) 대학 1학년용 카드를 결정적으로 생성한다.
#     카드 = 🎯목표/🧩쉬운설명/📥입력📤출력/(detect)보기별 행선지/🤖복사용 LLM 요청문/📜R 골격.
#     ★ goal/explain/input/output 만 사람이 큐레이트(_EASY_SEED). 나머지(보기 행선지·요청문·R)는
#       정본 필드(srp_intent·llm_prompt·verify_visualization·before_after·r_snippet)에서 파생 →
#       hallucination/Lock4 무위반. renderCPanel은 EASY[id]가 있으면 쉬운 카드, 없으면 기존 표시.
# ═════════════════════════════════════════════════════════════════════════════

def _load_raw_cunits() -> dict:
    d = json.loads((B.ROOT / "spec" / "c_units.json").read_text(encoding="utf-8"))
    if isinstance(d, dict):
        d = d.get("c_units", list(d.values()))
    return {e["c_id"]: e for e in d}


_RAW = _load_raw_cunits()

EASY_PILOT = ["c0210", "c0201", "c0203", "c0011", "c0120", "c0110"]

# 사람 큐레이트(쉬운 말). 코드/행선지/계약은 정본 파생이라 여기 없음.
_EASY_SEED = {
    "c0210": {
        "goal": "내 파일이 8가지 형식 중 무엇인지 알아내고, 컴퓨터가 ‘표로 읽을 수 있는지’ 판정한다.",
        "explain": "정리를 시작하려면 먼저 파일이 표(행·열)로 열리는지부터 확인해야 해요. CDISC 표준인지, "
                   "CRO가 준 엑셀인지, 아니면 스캔한 PDF처럼 아예 표가 아닌지에 따라 다음 작업이 완전히 "
                   "달라집니다. 표가 아니거나(NON-TABULAR) 깨졌으면(CORRUPTED) 여기서 정직하게 멈춥니다.",
        "input": "파일 그 자체 — 확장자, 시트 구조, 첫 줄(헤더) 모양",
        "output": "형식 이름 하나 (meta$a10_state) — 예: 'CRO-VENDOR'",
    },
    "c0201": {
        "goal": "이 데이터가 연구 하나인지, 여러 연구를 합친 것인지 판정한다.",
        "explain": "여러 연구를 합쳐 분석할 때는 환자 번호가 겹치지 않게 통일해야 해요. 그래서 먼저 ‘연구가 "
                   "몇 개인가’부터 봅니다. 합칠 때 번호 충돌을 풀 규칙이 없으면 사람에게 물어봐야 합니다(Q05).",
        "input": "시트·파일 목록과 연구 식별자(study id)",
        "output": "통합 수준 하나 (meta$a1_state) — SINGLE 또는 MULTI-*",
    },
    "c0203": {
        "goal": "사건이 ‘언제’ 일어났는지, 시간을 어떻게 쓸지 정한다(실제/예정/경과 등).",
        "explain": "약을 언제 먹고 언제 채혈했는지는 PK 분석의 핵심이에요. 실제 시각이 있는지, 예정 시각만 "
                   "있는지, 투약 후 경과시간인지에 따라 TIME 열을 만드는 방법이 달라집니다. 해석이 갈리면 "
                   "사람이 정하고(Q02), 시간이 아예 없으면 되살릴 수 없습니다(INVALID).",
        "input": "시간 관련 열(날짜·시각·nominal time)과 기준점(anchor) 정보",
        "output": "시간 정책 하나 (meta$a3_state) — 예: 'ACTUAL-PREFERRED'",
    },
    "c0011": {
        "goal": "각 행이 ‘측정값 없음(MDV=1)’인지 ‘유효 관측(MDV=0)’인지 표시하는 열을 만든다.",
        "explain": "NONMEM은 어떤 행이 실제 측정이고 어떤 행이 투약·결측인지 MDV 열로 구분해요. 투약·리셋 "
                   "행(EVID 1~4)은 측정이 아니니 MDV=1, 관측 행(EVID=0)은 값이 있으면 MDV=0, 비어 있으면 "
                   "MDV=1로 채웁니다. 값을 새로 ‘지어내지’ 않습니다.",
        "input": "EVID 열, 농도값(dv_value) 열",
        "output": "MDV 열(0 또는 1) 추가",
    },
    "c0120": {
        "goal": "옆으로 펼쳐진(wide) 농도 표를 NONMEM이 원하는 ‘세로로 긴(long)’ 표로 바꾼다.",
        "explain": "농도가 ‘Time, DRUG_A, DRUG_B …’처럼 분석물질마다 열로 펼쳐져 있으면 NONMEM이 못 읽어요. "
                   "한 행에 (시간, 분석물질, 농도) 하나씩 들어가도록 녹여야 합니다. 진단 마법사가 ‘표를 "
                   "정리하라(WU3 pivot)’고 할 때 하는 작업이에요.",
        "input": "wide 농도 표 — 분석물질(또는 개체)이 열로 펼쳐짐",
        "output": "long 표 — analyte_label·dv_value 열로 녹임(행 수 = 원본 × 분석물질 수)",
    },
    "c0110": {
        "goal": "따로 있는 투약 시트를 농도 표(main)에 공통 키로 붙인다.",
        "explain": "투약 기록과 농도 측정이 서로 다른 시트에 있을 때가 많아요. 같은 환자·방문을 가리키는 "
                   "공통 키(subject_id, visit)로 두 표를 합쳐야 한 줄에 ‘언제 얼마 투약하고 얼마 측정됐는지’가 "
                   "모입니다. 마법사의 WU4 dose-join이 이 작업입니다.",
        "input": "농도 표(main) + 투약 시트 + 공통 키(c0100에서 식별)",
        "output": "투약 정보(dose_amount, admin_route)가 붙은 통합 표",
    },
}

_AXIS_RE = re.compile(r"a(\d+)_state")
_ARROW_RE = re.compile(r"([A-Z][A-Z0-9\-]+)\s*→\s*(UNSUPPORTED|INVALID|Q\d+[A-Z]?)")


def _axis_of(raw: dict):
    """output_schema_delta의 '+meta[\'aN_state\']'에서 축 ID(A0..A10)를 추출(정본 파생)."""
    m = _AXIS_RE.search(raw.get("output_schema_delta", "") or "")
    return ("A" + m.group(1)) if m else None


def _easy_states(raw: dict, axis):
    """detect/axis-eval c의 보기별 행선지. 종료 매핑은 정본 llm_prompt의 'STATE→TERMINAL' 화살표에서만 취득."""
    if not axis or raw.get("kind") != "detect":
        return None
    tmap = dict(_ARROW_RE.findall(raw.get("llm_prompt", "") or ""))
    out = []
    for s in B.AXIS_STATES.get(axis, []):
        to = tmap.get(s)
        route = "go" if to is None else ("ask" if to.startswith("Q") else "stop")
        out.append({"code": s, "plain": GLOSSARY["state"].get(axis + "::" + s) or "",
                    "route": route, "to": to})
    return out


def _r_skeleton(raw: dict) -> str:
    """r_snippet 노출. detect의 미정의 helper 호출(예: detect_source_format)은 TODO 주석으로 전개."""
    r = raw.get("r_snippet", "") or ""
    if raw.get("kind") == "detect" and "<-" in r and "::" not in r and "(" in r:
        return ("# TODO: 아래 판별 로직(함수)을 직접 구현하세요 "
                "— ④의 🤖 요청문을 LLM에 주면 이 함수를 만들어 줍니다.\n" + r)
    return r


def _llm_request(raw: dict, seed: dict, states) -> str:
    """복사용 LLM 요청문 — 목표·입력·동작·보기·예시·출력계약·형식을 묶어 실행가능 R 산출을 유도."""
    action = " · ".join(_PLAIN_VOCAB.get(t, t) for t in str(raw.get("srp_intent", "")).split())
    ba = raw.get("before_after_toy_example") or {}
    lines = [
        "[목표] " + seed["goal"],
        "[내 데이터] " + seed["input"],
        "[해야 할 일] " + action + ".",
    ]
    if states:
        opts = "; ".join("%s = %s" % (s["code"], (s["plain"].split("→")[0].strip() or s["code"]))
                         for s in states)
        lines.append("[분류 보기] 아래 중 정확히 하나로 판정하고, 판별 규칙을 코드에 담아줘 — " + opts)
    if ba.get("before"):
        lines.append("[예시] 입력 « %s » → 출력 « %s »"
                     % (str(ba.get("before", "")).replace("\n", " / "),
                        str(ba.get("after", "")).replace("\n", " / ")))
    lines.append("[결과(출력 계약)] " + seed["output"]
                 + ("; 표로 읽을 수 없으면 왜 안 되는지 사유 문자열도 함께 반환." if states else "."))
    lines.append("[형식] 위를 수행하는 ‘실행 가능한 R 스크립트’를 dplyr/tidyr로 작성해줘. "
                 "각 줄에 한국어 주석을 달고, 없는 값을 새로 지어내지 마(IMPUTE 금지). "
                 "도우미 함수가 필요하면 정의까지 포함해줘.")
    return "\n".join(lines)


def easy_card(raw: dict) -> dict:
    seed = _EASY_SEED[raw["c_id"]]
    axis = _axis_of(raw)
    states = _easy_states(raw, axis)
    vv = raw.get("verify_visualization") or {}
    return {
        "goal": seed["goal"], "explain": seed["explain"],
        "input": seed["input"], "output": seed["output"],
        "axis": axis, "states": states,
        "pass_to": vv.get("pass_route_to"), "fail_to": vv.get("fail_route_to"),
        "llm_request": _llm_request(raw, seed, states),
        "r_skeleton": _r_skeleton(raw),
    }


EASY = {cid: easy_card(_RAW[cid]) for cid in EASY_PILOT}


def assert_glossary_complete():
    """ELES/CUNITS/QINFO/AXIS_STATES에 등장하는 모든 코드가 쉬운 말을 갖는지 검사(누락 시 빌드 실패)."""
    g = GLOSSARY
    missing = []

    def need(cat, key):
        if key not in g[cat] or not g[cat][key]:
            missing.append((cat, key))

    for cid, c in B.CUNITS.items():
        need("kind", c["kind"])
        if c["layer_pair"]:
            need("layer", c["layer_pair"])
        for tok in str(c["srp_intent"]).split():
            need("vocab", tok)
    for q in B.Q_IDS:
        need("qcode", q)
    for ax in B.AXIS_IDS:
        need("axis", ax)
        for s in B.AXIS_STATES.get(ax, []):
            need("state", ax + "::" + s)
    for n in B.BRANCH_IDS:
        need("node", n)
    for t in B.PROC_IDS:
        need("terminal", t)

    miss = sorted(set(missing))
    if miss:
        raise SystemExit("[build_html_v2] 용어집 미완 — 다음 항목에 쉬운 말이 없습니다:\n  "
                         + "\n  ".join("%s: %s" % (k, v) for k, v in miss))
    return True


# ═════════════════════════════════════════════════════════════════════════════
# 3. 색 교체 + PAGE_HEAD(쉬운 말·진단 버튼·추가 CSS)
# ═════════════════════════════════════════════════════════════════════════════
AMBER = "#E8820C"       # 기본 자동경로(실선) — 진한 앰버(원래 #FFD700)
TEAL = "#15B4C7"        # 질문 갈림길(점선, 하이라이트) — 청록(원래 #FFF8B0)
TEAL_DEEP = "#0E8A99"   # 질문 갈림길(점선, resting) — 딥 틸(원래 #c9920e)


def recolor(s: str) -> str:
    return s.replace("#FFD700", AMBER).replace("#FFF8B0", TEAL).replace("#c9920e", TEAL_DEEP)


_EXTRA_CSS = """
  /* ── index v2 추가 스타일(쉬운 말 배지·툴팁·진단 마법사) ── */
  .codechip{display:inline-block;font-family:Consolas,monospace;font-size:10px;color:#5a6b7a;background:#eef2f7;
            border:1px solid #d7dde3;border-radius:4px;padding:0 4px;margin-left:3px;cursor:help;vertical-align:middle}
  .muted{color:#8a97aa}
  .big{font-size:14px;font-weight:700;margin:1px 0 6px;color:#16314f}
  [data-tip]{position:relative}
  [data-tip]:hover::after{content:attr(data-tip);position:absolute;left:0;top:128%;z-index:10000;
     background:#1c2733;color:#fff;font-size:11px;font-weight:400;line-height:1.45;padding:6px 9px;border-radius:6px;
     width:max-content;max-width:300px;white-space:normal;box-shadow:0 3px 12px rgba(0,0,0,.28);pointer-events:none}
  .colornote{font-size:11px;color:#46535f;background:#f3f8fb;border:1px solid #d7e6ee;border-radius:6px;
     padding:6px 9px;margin-bottom:9px;line-height:1.55}
  .colornote b.amb{color:#E8820C} .colornote b.tl{color:#0E8A99}
  /* 진단 마법사 모달 */
  #wizMask,#glossMask{display:none;position:fixed;inset:0;background:rgba(20,30,40,.42);z-index:2000}
  #wizMask.on,#glossMask.on{display:flex;align-items:center;justify-content:center}
  #wizBox,#glossBox{background:#fff;border-radius:12px;max-width:700px;width:92%;max-height:88vh;overflow:auto;
     box-shadow:0 14px 44px rgba(0,0,0,.32)}
  #wizBox h2,#glossBox h2{font-size:15px;margin:0;padding:12px 16px;border-bottom:1px solid var(--line);
     display:flex;justify-content:space-between;align-items:center;background:#fafbfc;position:sticky;top:0}
  #wizBody,#glossBody{padding:13px 16px}
  .wq{margin:9px 0;padding:9px 11px;border:1px solid var(--line);border-radius:8px;background:#fafbfc}
  .wq .q{font-size:13px;font-weight:600;margin-bottom:6px;line-height:1.5}
  .wq label{font-size:12px;margin-right:16px;cursor:pointer}
  .wizact{display:flex;gap:8px;margin-top:13px;flex-wrap:wrap}
  #wizResult{margin-top:14px}
  .rescard{border:1px solid var(--line);border-radius:8px;padding:11px 13px;margin:9px 0;font-size:13px;line-height:1.65}
  .rescard.ok{background:#edf7ee;border-color:#bcdfc0}
  .rescard.stop{background:#fff4ec;border-color:#f0c9a8}
  .rescard h4{margin:0 0 6px;font-size:13.5px}
  .cchip{display:inline-block;font-family:Consolas,monospace;font-size:11px;background:#eaf1fb;border:1px solid #bcd2f0;
         border-radius:5px;padding:1px 6px;margin:2px;cursor:pointer;color:#1b4f8a}
  .cchip:hover{background:#d7e6fb}
  .gloss-sec{margin:10px 0}
  .gloss-sec h3{font-size:12.5px;margin:0 0 5px;color:#3a4651;border-bottom:1px solid var(--line);padding-bottom:3px}
  .gloss-row{font-size:12px;margin:3px 0;line-height:1.5}
  .gloss-row .gc{font-family:Consolas,monospace;font-size:11px;color:#1b4f8a;background:#eaf1fb;border-radius:4px;padding:0 5px;margin-right:6px}
  /* 쉬운 카드(EASY) + 궤도복귀/경로 breadcrumb */
  .easygoal{font-size:13.5px;font-weight:700;color:#16314f;background:#fff7ec;border:1px solid #f0d6ad;border-radius:6px;padding:7px 9px;margin-bottom:6px;line-height:1.5}
  .easyexp{font-size:12.5px;color:#3a4651;line-height:1.7;margin-bottom:7px}
  .straw{font-size:12px;line-height:1.7;padding:3px 0;border-bottom:1px dashed #eef2f7}
  .termstop{display:inline-block;font-size:11px;color:#455a64;background:#eceff1;border:1px solid #b0bec5;border-radius:5px;padding:0 6px;cursor:help}
  .llmreq{white-space:pre-wrap;background:#f7faff;border:1px solid #cfe0f5;border-radius:7px;padding:10px 11px;font-size:12px;line-height:1.65;color:#1f3550;font-family:Consolas,monospace;margin-top:6px}
  .copybtn{font-size:11px;padding:2px 8px;margin-bottom:2px}
  .rescard.onramp{background:#eef6ff;border-color:#bcd6f0}
  .rescard .step{margin-top:9px;padding:8px 10px;background:#fff;border:1px solid var(--line);border-radius:7px;font-size:12.5px;line-height:1.65}
  .rescard .manual{font-size:11px;color:#b3541e;background:#fff1e6;border:1px solid #f0c9a8;border-radius:5px;padding:1px 6px;margin-left:4px}
  .breadcrumb{margin:7px 0;padding:7px 9px;background:#fffaf2;border:1px solid #f0dcc0;border-radius:7px;font-size:12px;line-height:2.1}
  .breadcrumb.dotted{background:#f4f8fc;border-style:dashed;border-color:#bcd2f0}
  .pnode{display:inline-block;font-weight:700;font-size:11px;border-radius:5px;padding:1px 7px}
  .pnode.start{background:#ffe1a8;color:#7a4b00}
  .pnode.goal{background:#43a047;color:#fff}
  .parrow{color:#E8820C;font-weight:700}
  .parrow.d{color:#7d9bbb}
"""


def page_head_v2() -> str:
    ph = recolor(B.PAGE_HEAD)
    ph = ph.replace("<title>pmx-dt · NONMEM-ready decision tree (Phase 8 · 전체 tree)</title>",
                    "<title>pmx-dt · 쉬운 설명 뷰 (index v2)</title>")
    ph = ph.replace("<h1>pmx-dt · decision tree</h1>",
                    '<h1>pmx-dt · 쉬운 설명 뷰 <span style="font-weight:400;color:#8a97aa;font-size:11px">(index v2)</span></h1>')
    ph = ph.replace("NONMEM-ready data wrangling · 전체 tree (Phase 8)",
                    "raw 데이터 → NONMEM-ready 정리 지도 · 클릭하면 쉬운 말로 설명")
    # 토프바에 진단/용어집 버튼 추가(선택 해제 버튼 앞)
    ph = ph.replace(
        '<button class="btn" id="clearSel" type="button">선택 해제</button>',
        '<button class="btn" id="wizardBtn" type="button" style="background:#e8f4ff;border-color:#9cc6f0;font-weight:700">🔍 내 파일 진단</button>\n'
        '  <button class="btn" id="glossBtn" type="button" style="background:#f1f0fb;border-color:#cfc8ee">📖 용어집</button>\n'
        '  <button class="btn" id="clearSel" type="button">선택 해제</button>')
    # 안내 기본 문구(쉬운 말)
    ph = ph.replace("노드를 클릭하면 경로(N0→현재)가 표시됩니다.",
                    "점(작업)을 클릭하면 그 일이 무엇인지 + 끝까지 가는 길이 색으로 표시됩니다. 처음이면 “🔍 내 파일 진단”부터.")
    ph = ph.replace("</style>", _EXTRA_CSS + "\n</style>")
    return ph


# ═════════════════════════════════════════════════════════════════════════════
# 4. APP_JS 오버라이드 — 쉬운 말 패널 재작성 + 색 안내 + 진단 마법사 + 용어집
#    (build_html.py의 함수들을 window.* 재할당으로 교체. 데이터는 전부 전역 globals 참조.)
# ═════════════════════════════════════════════════════════════════════════════
_V2_OVERRIDE = r'''<script>
"use strict";
/* ===== index v2 override: 쉬운 말 패널 + 색 안내 + 진단 마법사 + 용어집 ===== */
(function(){
  function E(s){ return esc(s); }
  function sect(title, body){ return '<div class="sect"><h3>'+title+'</h3><div class="body">'+body+'</div></div>'; }
  function kv(k, v){ return '<div class="kv"><span class="k">'+k+'</span> · '+v+'</div>'; }
  function gloss(cat, code){ var m=(GLOSSARY[cat]||{}); return m[code]||""; }
  function plainSrp(srp){
    var voc=GLOSSARY.vocab||{};
    return String(srp||"").split(/\s+/).filter(Boolean).map(function(t){ return voc[t]||t; }).join(" · ");
  }
  function chip(code, cat){
    var tip;
    if(cat==="srp") tip=plainSrp(code);
    else if(cat==="c") tip=((CUNITS[code]||{}).c_name_ko)||code;
    else tip=gloss(cat, code);
    return '<span class="codechip" data-tip="'+E(tip||code)+'">'+E(code)+'</span>';
  }
  function qChip(q){ return '<span class="pill q codechip" data-tip="'+E(gloss("qcode",q)||q)+'">'+E(q)+'</span>'; }
  function stateChip(ax, s){ return '<span class="pill codechip" data-tip="'+E(gloss("state", ax+"::"+s)||s)+'">'+E(s)+'</span>'; }
  /* onward 라우팅 해소(모든 노드): 통과=c칩/친절문구 · 막힘=질문(Q) vs ✋정당한 종료 구분 */
  function isCid(x){ return /^c\d{4}$/.test(String(x||"")); }
  function isQc(x){ return /^Q\d+[A-Z]?$/.test(String(x||"")); }
  function passChip(p){
    if(!p) return '<span class="pill pass">다음 작업으로 계속</span>';
    if(isCid(p)) return '<span class="pill pass">→</span> '+chip(p,"c");
    if(String(p)==="next axis") return '<span class="pill pass">다음 축 평가로 계속 → 🏁</span>';
    return '<span class="pill pass">'+E(p)+'</span>';
  }
  function failChip(f){
    if(!f) return '<span class="pill">없음(이 작업은 막히지 않음)</span>';
    if(isQc(f)) return qChip(f);
    return '<span class="termstop" data-tip="자동 처리 대상이 아니라 여기서 정직하게 종료합니다(결함이 아니라 정당한 종료).">✋ 정당한 종료 · '+E(f)+'</span>';
  }
  function colorNote(){
    return '<div class="colornote">길 색 안내 — <b class="amb">굵은 앰버 실선</b> = 자동으로 흘러가는 <b>기본 경로</b>(사람 손 불필요) · '
         + '<b class="tl">청록 점선</b> = 여기서 문제가 있으면 <b>‘사람이 결정해야 하는 질문(Q)’</b>으로 빠지는 갈림길.</div>';
  }
  window.__v2_colorNote = colorNote;

  /* ---- (c 패널) 변환/감지/검사/분기 — 쉬운 말 4섹션 ---- */
  window.renderCPanel = function(id){
    var c=CUNITS[id]; if(!c) return window.renderNodePanel(id,"node");
    if(window.EASY && EASY[id]) return renderEasyCPanel(id, c, EASY[id]);
    var h=colorNote();
    var chk=(c.precondition_checklist_ko||[]).map(function(t,i){
      return '<li><input type="checkbox" class="ckbox" data-i="'+i+'" id="ck'+i+'"><label for="ck'+i+'">'+E(t)+'</label></li>';
    }).join("");
    h+=sect("① 시작 전 — 내 데이터가 이 작업을 받을 준비가 됐는지 확인",
            '<ul class="chklist" id="chk">'+chk+'</ul><div class="badge-ok" id="chkbadge">✓ 위치 확인됨</div>');
    var b="";
    b+=kv("이름", "<b>"+E(c.c_name_ko)+"</b>");
    b+=kv("하는 일", plainSrp(c.srp_intent)+" "+chip(c.srp_intent,"srp"));
    b+=kv("작업 종류", E(gloss("kind",c.kind))+" "+chip(c.kind,"kind"));
    b+=kv("드는 품(비용)", String(c.cost));
    b+=kv("정리 단계", E(gloss("layer",c.layer_pair))+" "+chip(c.layer_pair,"layer"));
    b+=kv("먼저 끝나야 할 작업", c.requires_detection_by
            ? (chip(c.requires_detection_by,"c")+' <span class="muted">(이 감지가 선행되어야 함)</span>')
            : '<span class="muted">없음(바로 시작 가능)</span>');
    b+=kv("영향 받는 시나리오", "<b>"+c.influence+"</b>개 경로");
    b+='<div class="snlabel">이 작업을 시키는 지시문(사람/LLM용)</div><div class="prompt">'+E(c.llm_prompt)+'</div>';
    b+=kv("원래 코드", chip(c.c_id,"c")+' · <span class="muted">근거</span> '+E(c.ref));
    h+=sect("② 이 작업이 무슨 일을 하나", b);
    if(c.kind==="transform"){
      h+=sect("③ 고치기 전 / 후 — 앰버 칸이 바뀐 부분", renderBeforeAfter(c.before,c.after));
    }else{
      h+=sect("③ 무엇을 검사하고, 통과하면 어디로 · 막히면 어디로", window.renderVV(c.verify_visualization,c.can_route_to_q));
    }
    h+=sect("④ 실제 코드 예시 (위 R · 아래 Python)",
            '<div class="snlabel">R</div><pre class="snip">'+hlComments(c.r_snippet)+'</pre>'
            +'<div class="snlabel">Python</div><pre class="snip">'+hlComments(c.python_snippet)+'</pre>');
    return h;
  };

  window.renderVV = function(vv, canQ){
    if(!vv){
      var q=(canQ||[]);
      return '<div class="muted">이 작업은 ‘검사’가 아니라 변환/분기라 검사 장면이 없습니다.</div>'
        + (q.length ? kv("막히면 갈 수 있는 질문", q.map(qChip).join(" "))
                    : kv("다음", '<span class="pill pass">정리 후 다음 작업으로 계속 → 🏁</span>'));
    }
    var h=kv("검사 대상 열", (vv.target_columns||[]).map(function(x){return '<span class="pill">'+E(x)+'</span>';}).join(" "));
    h+=kv("합격 기준", E(vv.criterion_predicate_ko));
    h+=kv("통과하면 →", passChip(vv.pass_route_to));
    h+=kv("막히면(실패) →", failChip(vv.fail_route_to));
    return h;
  };

  /* ---- (쉬운 카드) 파일럿 c — 🎯목표/🧩설명/보기 행선지/🤖요청문/R 골격 ---- */
  function renderEasyCPanel(id, c, ez){
    var h=colorNote();
    var chk=(c.precondition_checklist_ko||[]).map(function(t,i){
      return '<li><input type="checkbox" class="ckbox" data-i="'+i+'" id="ck'+i+'"><label for="ck'+i+'">'+E(t)+'</label></li>';
    }).join("");
    h+=sect("① 시작 전 — 내 데이터가 이 작업을 받을 준비가 됐는지 확인",
            '<ul class="chklist" id="chk">'+chk+'</ul><div class="badge-ok" id="chkbadge">✓ 위치 확인됨</div>');
    var b='<div class="easygoal">🎯 '+E(ez.goal)+'</div>';
    b+='<div class="easyexp">🧩 '+E(ez.explain)+'</div>';
    b+=kv("📥 들어오는 것(입력)", E(ez.input));
    b+=kv("📤 나가는 것(출력)", E(ez.output));
    b+=kv("작업 종류", E(gloss("kind",c.kind))+" "+chip(c.kind,"kind"));
    b+=kv("원래 코드", chip(c.c_id,"c")+' · <span class="muted">근거</span> '+E(c.ref));
    h+=sect("② 이 작업이 무슨 일을 하나 (쉬운 말)", b);
    if(ez.states){
      var rows=ez.states.map(function(s){
        var rt = (s.route==="go") ? '<span class="pill pass">→ 계속</span>'
               : (s.route==="ask") ? ('→ '+qChip(s.to))
               : ('<span class="termstop">✋ 정당한 종료 · '+E(s.to)+'</span>');
        return '<div class="straw">'+stateChip(ez.axis,s.code)+' <span class="muted">'+E(s.plain||"")+'</span> '+rt+'</div>';
      }).join("");
      h+=sect("③ 보기 — 내 파일이 어디에 해당하고, 그러면 어디로 가나",
              rows+'<div style="margin-top:7px">'+kv("통과하면 →", passChip(ez.pass_to))+kv("막히면 →", failChip(ez.fail_to))+'</div>');
    }else{
      h+=sect("③ 고치기 전 / 후 — 앰버 칸이 바뀐 부분", renderBeforeAfter(c.before,c.after));
    }
    h+=sect("④ 🤖 LLM에게 이대로 복사해 요청하세요 — 이 작업에 맞는 R 스크립트를 만들어 줍니다",
            '<button class="btn copybtn" data-copy="llmreq_'+E(id)+'">📋 복사</button>'
            +'<pre class="llmreq" id="llmreq_'+E(id)+'">'+E(ez.llm_request)+'</pre>');
    h+=sect("⑤ 참고 코드 골격 (위 요청문으로 받은 R을 검증·비교할 때 — 위 R · 아래 Python)",
            '<div class="snlabel">R</div><pre class="snip">'+hlComments(ez.r_skeleton)+'</pre>'
            +'<div class="snlabel">Python</div><pre class="snip">'+hlComments(c.python_snippet)+'</pre>');
    return h;
  }

  /* ---- (Q 패널) 질문(Q-code) — 쉬운 말 ---- */
  window.renderQPanel = function(id){
    var q=QINFO[id]; if(!q) return window.renderTerminalPanel(id);
    var defer=(q.q_status==="unreached");
    var h=colorNote();
    h+=sect("이 질문은? "+chip(id,"qcode")+(defer?' <span class="deferbadge">아직 연결 안 됨</span>':''),
            '<div class="big">'+E(gloss("qcode",id)||q.name)+'</div>'
            + kv("원래 이름", E(q.name))
            + kv("언제 생기나(조건)", E(q.trigger_condition)));
    var reach;
    if(defer){
      reach='<div class="muted">아직 이 질문으로 가는 작업이 연결되지 않은 자리표시입니다(후속 작업).</div>';
    }else if(q.reach && q.reach.length){
      reach=q.reach.map(function(r){
        return '<div class="reachrow">'+chip(r.from,"c")+' <span class="muted">('+E(gloss("kind",r.from_kind)||r.from_kind)+')</span> → '+E(id)+' · 시나리오 '+r.strand_count+'</div>';
      }).join("");
    }else{
      reach='<div class="kv">연결된 작업: '+(q.incoming_wired_c||[]).map(function(x){return chip(x,"c");}).join(" ")+'</div>';
    }
    h+=sect("① 어떻게 여기로 오나 — 어떤 작업에서 이 질문으로 빠지는지", reach
            + kv("이 질문이 영향 주는 시나리오", "<b>"+q.influence+"</b>개"));
    var clar=(q.clarification_to_sponsor||[]).map(function(t){return '<li>'+E(t)+'</li>';}).join("");
    h+=sect("② 스폰서/데이터 주인에게 물어볼 것", '<ul style="margin:0;padding-left:18px;font-size:13px;line-height:1.6">'+clar+'</ul>');
    h+=sect("③ 사람이 내려야 할 결정", E(q.human_decision_point)
            + kv("드는 비용/노력", "비용 "+q.routing_cost+" · 노력 "+E(q.human_effort_score)+"/10"));
    var rec=q.recover_to_c_id, recWired=(rec && CUNITS[rec]);
    var rh='답을 받은 뒤 돌아오는 지점: <b>'+E(rec||"—")+'</b>';
    if(defer){
      rh+='<div class="kv muted">이 질문은 아직 미연결이라 복귀선도 생략됩니다.</div>';
    }else if(recWired){
      rh+=' <button class="btn" id="recoverBtn" data-to="'+E(rec)+'">↩ '+E(rec)+' 로 돌아가기</button>';
      rh+='<div class="kv" style="color:#1565c0">트리에 ↩ 파랑 점선으로 표시 — <b>자동이 아니라</b> 사람이 답한 뒤 다시 들어가는 길입니다.</div>';
    }else{
      rh+='<div class="kv" style="color:#b35a16">복귀 지점 '+E(rec)+' 는 아직 구현 범위 밖이라 선은 생략(숨김 0).</div>';
    }
    h+=sect("④ 답을 받은 뒤 어디로 돌아오나 (사람 개입 후)", rh);
    return h;
  };

  /* ---- (노드 패널) 관문 N/축 A/stage/state — 쉬운 말 ---- */
  window.renderNodePanel = function(id, kind){
    var info=NODEINFO[id];
    if(kind==="state"){
      var p=id.split("::"), ax=p[0], s=p[1]||id, pl=gloss("state", id);
      return colorNote()+sect("이 칸은? "+chip(ax,"axis")+" 의 상태 · "+E(s),
        (pl?'<div class="big">'+E(pl)+'</div>':'')
        +'이 칸을 지나는 시나리오는 '+E(ax)+' 축에서 <b>'+E(s)+'</b>로 분류됩니다.');
    }
    if(kind==="stage"){
      return colorNote()+sect("정규화 stage란?",
        '글자·인코딩·셀 같은 ‘가장 바닥’을 정리하는 묶음 단계입니다. 묶인 개별 작업(c)은 따로 점으로 보입니다.')
        +sect("참고", '묶음 노드화는 후속 결정 대기(GAP-27B). 지금은 개별 c로 표시합니다.');
    }
    if(!info) return sect("노드", E(id));
    var isAxis=(kind==="axis");
    var pl=isAxis?gloss("axis",id):gloss("node",id);
    var h=colorNote();
    h+=sect("역할 "+chip(id, isAxis?"axis":"node"),
        (pl?'<div class="big">'+E(pl)+'</div>':'')+E(info.role)+(info.ref?kv("근거",E(info.ref)):''));
    var bm=E(info.bm);
    if(info.states){
      bm+='<div class="navrow">'+info.states.map(function(s){return stateChip(id,s);}).join("")+'</div>';
      bm+='<button class="btn" id="axisToggle" data-ax="'+E(id)+'">'+(state.expandedAxes.indexOf(id)>=0?"▲ 상태 접기":"▼ 상태 펼치기")+'</button>';
    }
    h+=sect(isAxis?"어떤 상태로 갈라지나":"여기서 갈라지는/합쳐지는 방식", bm);
    h+=sect("영향 받는 시나리오 수", "<b>"+info.strands+"</b>개 경로");
    return h;
  };

  window.renderTerminalPanel = function(id){
    var info=NODEINFO[id]||{role:"종착", bm:"", strands:"—"};
    var pl=gloss("terminal",id);
    return colorNote()+sect("종착점 "+chip(id,"terminal"),
        (pl?'<div class="big">'+E(pl)+'</div>':'')+E(info.role)+(info.ref?kv("근거",E(info.ref)):''))
      +sect("영향 받는 시나리오 수","<b>"+info.strands+"</b>개 경로");
  };

  /* ===== 진단 마법사(src/adapter 1:1 미러) ===== */
  var WQ=[
    {k:"tidy", q:"1) 농도(concentration) 데이터 시트가 <b>1행=헤더</b>이고, 그 헤더에 <b>시간 열</b>과 <b>농도 열</b>이 둘 다 있는 <b>깔끔한 표</b>(검량/QA 행이 안 섞임)인가요?"},
    {k:"qa", q:"2) 그 시트 <b>맨 왼쪽 첫 열</b>에 Standard · DBLK · BLK · QC · Calibration · Blank 같은 <b>검량/QA 행</b>이 실제 샘플과 섞여 있나요?"},
    {k:"param", q:"3) 그 표가 농도 원자료가 아니라 Cmax · AUC 같은 <b>‘파라미터 요약’</b>(열에 Parameters · Unit, 값은 Mean)인가요?"},
    {k:"subject_wide", q:"4) 농도가 <b>‘시간=행, 동물/사람=열’</b>(예: Time, Animal1, Animal2 …)로 옆으로 펼쳐져 있나요?"},
    {k:"has_subject", q:"5) 그 표에 <b>개체(사람/동물) 번호 열</b>(subject / animal / ID 등)이 있나요?"},
    {k:"multi_or_merged", q:"6) 엑셀에 <b>시트가 2개 이상</b>이거나 <b>병합된 셀</b>이 있나요?"},
    {k:"non_ascii", q:"7) 시트 이름이나 셀에 <b>한글/특수문자</b>가 있나요?"},
    {k:"unit_col", q:"8) 단위가 <b>별도 ‘Unit’ 열</b>로 들어 있나요?"},
    {k:"blq", q:"9) 농도 칸에 <b>‘BLQ’ · ‘&lt;LLOQ’ · ‘ND’</b> 같은 토큰이 단독으로 들어 있나요?"},
    {k:"bw_sheet", q:"10) <b>체중(BW / body weight / 체중)</b> 정보가 <b>별도 시트</b>로 있나요?"}
  ];
  function wizardVerdict(a){
    var faithful=!!a.tidy;
    var chosen={};
    WIZARD.file_property_c.forEach(function(c){ chosen[c]=1; });
    if(faithful){
      WIZARD.data_dependent_c.forEach(function(c){
        var req=WIZARD.precond[c];
        var ok=(req==="none")||(req==="time")||(req==="dv")||(req==="subject+time+dv" && !!a.has_subject);
        if(ok) chosen[c]=1;
      });
    }
    var cseq=WIZARD.canon_order.filter(function(c){ return chosen[c]; });
    var qset={};
    cseq.forEach(function(c){ ((CUNITS[c]||{}).can_route_to_q||[]).forEach(function(q){ qset[q]=1; }); });
    return {faithful:faithful, entry:"N0", c_sequence:cseq, qcodes:Object.keys(qset), honest_stop:!faithful};
  }
  /* 표가 tidy가 됐다고 가정했을 때의 경로(=궤도 복귀 후 '예상 경로'). wizardVerdict의 faithful 분기와 동일 규칙. */
  function projectedFaithfulSeq(a){
    var chosen={};
    WIZARD.file_property_c.forEach(function(c){ chosen[c]=1; });
    WIZARD.data_dependent_c.forEach(function(c){
      var req=WIZARD.precond[c];
      var ok=(req==="none")||(req==="time")||(req==="dv")||(req==="subject+time+dv" && !!a.has_subject);
      if(ok) chosen[c]=1;
    });
    return WIZARD.canon_order.filter(function(c){ return chosen[c]; });
  }
  /* 출발점 N0 → c들 → 🏁 nonmem-ready 까지의 경로를 한 줄로. dotted=true 면 '예상 경로'(점선). */
  function pathBreadcrumb(seq, dotted){
    var arrow=dotted?' <span class="parrow d">⇢</span> ':' <span class="parrow">→</span> ';
    var parts=['<span class="pnode start">N0</span>'];
    (seq||[]).forEach(function(c){ parts.push('<span class="cchip" data-node="'+E(c)+'">'+E(c)+'</span>'); });
    parts.push('<span class="pnode goal">🏁 nonmem-ready</span>');
    return '<div class="breadcrumb'+(dotted?' dotted':'')+'">'+parts.join(arrow)+'</div>';
  }
  function buildWizard(){
    var mask=document.createElement("div"); mask.id="wizMask";
    var qhtml=WQ.map(function(w){
      return '<div class="wq"><div class="q">'+w.q+'</div>'
        +'<label><input type="radio" name="wq_'+w.k+'" value="y"> 예</label>'
        +'<label><input type="radio" name="wq_'+w.k+'" value="n" checked> 아니오</label></div>';
    }).join("");
    mask.innerHTML='<div id="wizBox"><h2>🔍 내 파일 진단 — 어디서 시작할까요?'
      +'<button class="btn" id="wizClose">×</button></h2><div id="wizBody">'
      +'<div class="muted" style="font-size:12px;margin-bottom:8px">파일을 올리지 않습니다. 아래 질문에 답하면, 정본 Python 어댑터(<span class="mono">src/adapter</span>)와 <b>똑같은 규칙</b>으로 시작 지점을 알려줍니다. (1번이 ‘예’이면 2~4번은 보통 ‘아니오’ — 한 시트는 한 종류)</div>'
      +qhtml
      +'<div class="wizact"><button class="btn" id="wizGo" style="background:#2f6fde;color:#fff;border-color:#2f6fde;font-weight:700">진단하기</button>'
      +'<button class="btn" id="wizReset2">답 지우기</button></div><div id="wizResult"></div></div></div>';
    document.body.appendChild(mask);
    mask.addEventListener("click", function(e){ if(e.target===mask) closeWiz(); });
    document.getElementById("wizClose").addEventListener("click", closeWiz);
    document.getElementById("wizGo").addEventListener("click", runWiz);
    document.getElementById("wizReset2").addEventListener("click", function(){
      WQ.forEach(function(w){ var n=document.querySelector('input[name="wq_'+w.k+'"][value="n"]'); if(n) n.checked=true; });
      document.getElementById("wizResult").innerHTML="";
    });
  }
  function openWiz(){ document.getElementById("wizMask").classList.add("on"); }
  function closeWiz(){ document.getElementById("wizMask").classList.remove("on"); }
  function readAnswers(){
    var a={};
    WQ.forEach(function(w){ var el=document.querySelector('input[name="wq_'+w.k+'"]:checked'); a[w.k]=!!(el&&el.value==="y"); });
    return a;
  }
  function cSeqChips(seq){
    return seq.map(function(c){
      var nm=((CUNITS[c]||{}).c_name_ko)||"";
      return '<span class="cchip" data-node="'+E(c)+'" title="'+E(nm)+'">'+E(c)+'</span>';
    }).join("");
  }
  function runWiz(){
    var a=readAnswers();
    var v=wizardVerdict(a);
    var box=document.getElementById("wizResult");
    var html="";
    if(v.faithful){
      var qhtml=v.qcodes.length? v.qcodes.map(qChip).join(" ") : '<span class="muted">없음(축이 깨끗하면 질문 없이 통과)</span>';
      html+='<div class="rescard ok"><h4>✅ 시작 지점: <b>N0</b> → 따라가면 <b>🏁 nonmem-ready</b></h4>'
        +'당신 파일은 <b>깔끔한 tidy 표</b>라 도구가 자동 정리 밴드로 들어갑니다. 아래 길을 끝까지 따라가면 완성에 도달합니다.'
        + pathBreadcrumb(v.c_sequence, false)
        +'<div style="margin-top:8px"><b>이 파일에 적용되는 정리·검사 작업</b> (클릭하면 설명):<br>'+cSeqChips(v.c_sequence)+'</div>'
        +'<div style="margin-top:8px"><b>정리하면서 마주칠 수 있는 결정 질문(Q)</b>:<br>'+qhtml+'</div>'
        +'<div style="margin-top:8px" class="muted">파일만으로 풀리는 축: <b>A1 / A3 / A5 / A10</b>. 나머지(A0 / A2 / A4 / A6 / A7 / A8 / A9)는 '
        +'<b>분석 목적 · 정책</b>이라 <b>당신이 정해야</b> 합니다(파일만 봐선 모름 — over-read 금지).</div></div>';
    }else{
      var reasons=[], wus=[];
      if(a.qa){ reasons.push("검량/QA 블록이 실샘플과 섞여 있음"); wus.push("WU1 QA-strip(검량·QC 행 제거)"); wus.push("WU3 pivot(QA 제거 후 wide→long)"); }
      if(a.param){ reasons.push("파라미터 요약 시트(원자료 아님)"); wus.push("WU1 param-summary-reserve(건너뛰고 보존 — drop 아님)"); }
      if(a.subject_wide){ reasons.push("subject-wide(시간=행, 개체=열) 배치"); wus.push("WU3 pivot-wide-to-long"); }
      if(a.bw_sheet || a.qa || a.param || a.subject_wide){ wus.push("WU4 dose-bw-join(체중/용량 시트 결합)"); }
      if(!a.qa && !a.param && !a.subject_wide){ reasons.push("알 수 없는 구조(tidy로 못 읽음)"); }
      var uniq=wus.filter(function(x,i){ return wus.indexOf(x)===i; });
      var proj=projectedFaithfulSeq(a);
      html+='<div class="rescard onramp"><h4>🛟 궤도 복귀 경로 — 막다른 길이 아닙니다</h4>'
        +'당신 파일은 아직 도구가 자동으로 다루는 <b>깔끔한 tidy 표</b>가 아닙니다. 하지만 dead-end가 아니라, 아래 <b>2단계</b>로 궤도에 올리면 <b>🏁 nonmem-ready</b>까지 갈 수 있어요.'
        +'<div style="margin-top:8px"><b>감지된 이유</b>: '+(reasons.length?reasons.map(E).join(" / "):"—")+'</div>'
        +'<div class="step"><b>1단계 — 표 정리(on-ramp)</b> <span class="manual">⚠️ 이 정리는 아직 도구가 자동으로 못 함 — 당신/LLM이 먼저 (GAP-37)</span><br>'+(uniq.length?uniq.map(E).join("<br>"):"—")+'</div>'
        +'<div class="step"><b>2단계 — 표가 tidy가 되면 이어지는 자동 경로</b> <span class="muted">(아래는 <b>예상 경로</b> · 점선)</span>'+pathBreadcrumb(proj, true)+'</div>'
        +'<div style="margin-top:8px">지금 도구가 자동으로 진단하는 작업: '+cSeqChips(v.c_sequence)+' <span class="muted">(파일 속성만 — 1단계 정리 전이라 여기까지)</span></div>'
        +'<div style="margin-top:8px" class="muted">✅ 정확한 자동 진단은 정본 Python 어댑터로: <span class="mono">python -m src.adapter &lt;내파일.xlsx&gt; --recipe</span></div></div>';
    }
    box.innerHTML=html;
    Array.prototype.forEach.call(box.querySelectorAll(".cchip"), function(ch){
      ch.addEventListener("click", function(){
        var n=cy.getElementById(ch.getAttribute("data-node"));
        if(n && n.length){ closeWiz(); onNodeTap(n); }
      });
    });
    var ids=["N0"].concat(v.c_sequence).concat(v.qcodes||[]).concat(["AUTO"]);
    highlightSet(ids);
  }
  function highlightSet(ids){
    if(typeof clearHighlight==="function") clearHighlight();
    var col=cy.collection();
    ids.forEach(function(id){ var n=cy.getElementById(id); if(n && n.length) col=col.union(n); });
    if(!col.length) return;
    cy.elements().addClass("dim");
    col.removeClass("dim").addClass("hl");
    var inter=col.edgesWith(col);
    inter.removeClass("dim");
    inter.forEach(function(e){ e.addClass(e.data("conditional")?"hlCond":"hlSingle"); });
    var n0=cy.getElementById("N0"); if(n0 && n0.length){ n0.removeClass("hl").addClass("current"); }
    try{ cy.animate({fit:{eles:col.union(inter), padding:60}}, {duration:300}); }catch(e){ cy.fit(col.union(inter),60); }
  }

  /* ===== 용어집 모달 ===== */
  function buildGloss(){
    var mask=document.createElement("div"); mask.id="glossMask";
    function rows(catLabel, obj, order){
      var keys=order||Object.keys(obj);
      var body=keys.map(function(k){
        var v=obj[k]; if(!v) return "";
        return '<div class="gloss-row"><span class="gc">'+E(k.indexOf("::")>=0?k.split("::")[1]:k)+'</span>'+E(v)+'</div>';
      }).join("");
      return '<div class="gloss-sec"><h3>'+catLabel+'</h3>'+body+'</div>';
    }
    var statesByAxis="";
    (Object.keys(GLOSSARY.axis)).forEach(function(ax){
      var sub=Object.keys(GLOSSARY.state).filter(function(k){ return k.indexOf(ax+"::")===0; });
      if(sub.length){
        var b=sub.map(function(k){ return '<div class="gloss-row"><span class="gc">'+E(k.split("::")[1])+'</span>'+E(GLOSSARY.state[k])+'</div>'; }).join("");
        statesByAxis+='<div class="gloss-sec"><h3>축 '+E(ax)+' 의 상태 — '+E(GLOSSARY.axis[ax])+'</h3>'+b+'</div>';
      }
    });
    mask.innerHTML='<div id="glossBox"><h2>📖 용어집 — 어려운 말 쉬운 말 대응<button class="btn" id="glossClose">×</button></h2><div id="glossBody">'
      +'<div class="muted" style="font-size:12px;margin-bottom:8px">화면 곳곳의 <span class="codechip">코드</span>에 마우스를 올려도 같은 설명이 뜹니다.</div>'
      +rows("관문 N0–N7 (큰 단계)", GLOSSARY.node)
      +rows("축 A0–A10 (판단 기준)", GLOSSARY.axis)
      +rows("작업 종류", GLOSSARY.kind)
      +rows("정리 단계(layer)", GLOSSARY.layer)
      +rows("종착점", GLOSSARY.terminal)
      +rows("질문 Q-code", GLOSSARY.qcode)
      +statesByAxis
      +rows("작업 용어(srp_intent의 동사/명사)", GLOSSARY.vocab)
      +'</div></div>';
    document.body.appendChild(mask);
    mask.addEventListener("click", function(e){ if(e.target===mask) mask.classList.remove("on"); });
    document.getElementById("glossClose").addEventListener("click", function(){ mask.classList.remove("on"); });
  }

  /* ===== 범례 + 경계 배너 쉬운 말로 다시 그리기 ===== */
  function redrawLegend(){
    function lg(label, sw){ return '<span class="lg"><span class="sw" style="'+sw+'"></span>'+label+'</span>'; }
    var shapes=[
      ["동그라미 = 변환(고치기)","background:#7fb2ff;border-radius:50%"],
      ["점선 동그라미 = 감지/검사","background:#bcd9ff;border-radius:50%;border-style:dashed"],
      ["육각 = 분기 결정","background:#ffcf80"],
      ["연한 육각 = 축 질문(A0~A10)","background:#ffe1a8"],
      ["다이아 = 큰 관문(N0~N7)","background:#ffb74d"]
    ];
    var term=[
      ["완성(자동/정리)","background:#43a047"],
      ["사람 결정 대기","background:#ffa726"],
      ["질문(Q) 답변 필요","background:#ef5350"],
      ["사용 불가(INVALID)","background:#546e7a"]
    ];
    var edges=[
      ["자동 기본 경로 (앰버 실선)","background:#E8820C"],
      ["질문(Q)으로 빠지는 갈림길 (청록 점선)","background:#15B4C7;border-style:dashed"],
      ["사람 개입 후 복귀 (파랑 점선)","background:#1976d2;border-style:dashed"]
    ];
    function row(items){ return items.map(function(x){ return lg(x[0], x[1]); }).join(""); }
    var el=document.getElementById("legend");
    if(el) el.innerHTML='<span class="grp">노드 모양</span>'+row(shapes)
      +'<span class="sep"></span><span class="grp">종착</span>'+row(term)
      +'<span class="sep"></span><span class="grp">길(클릭 시)</span>'+row(edges);
    var bn=document.getElementById("boundary"), b=window.DT_BANNER||{};
    if(bn) bn.innerHTML='<b>쉽게 말해</b> — 이 그림은 엉망인 raw 데이터에서 NONMEM 분석용 <b>깔끔한 데이터</b>까지 가는 모든 갈림길을 한 장에 그린 <b>지도</b>입니다. '
      +'점(작업)을 클릭하면 그 일이 무엇인지·다음에 어디로 가는지 쉬운 말로 풀어줍니다. '
      +'· 전체 시나리오 <b>'+b.total_strands+'개</b> 중 자동 완성 <b>'+b.complete+'</b> · 사람 결정 대기(Q) <b>'+b.quarantine+'</b> · 사용 불가 <b>'+b.invalid+'</b>. '
      +'→ <b>“🔍 내 파일 진단”</b> 버튼으로 내 파일이 어디서 시작하는지 확인하세요.';
  }

  /* ===== 부팅: 모달 생성 + 버튼 연결 + 범례 갱신 + 현재 패널 v2로 다시 그리기 ===== */
  buildWizard();
  buildGloss();
  redrawLegend();
  var wb=document.getElementById("wizardBtn"); if(wb) wb.addEventListener("click", openWiz);
  var gb=document.getElementById("glossBtn"); if(gb) gb.addEventListener("click", function(){ document.getElementById("glossMask").classList.add("on"); });
  /* 🤖 요청문 복사 버튼(이벤트 위임 — 패널은 매번 새로 그려지므로) */
  document.addEventListener("click", function(e){
    var btn=(e.target && e.target.closest) ? e.target.closest(".copybtn") : null;
    if(!btn) return;
    var el=document.getElementById(btn.getAttribute("data-copy")); if(!el) return;
    var txt=el.innerText||el.textContent||"";
    function flash(){ var t=btn.getAttribute("data-lbl"); if(!t){ t=btn.textContent; btn.setAttribute("data-lbl",t); } btn.textContent="✓ 복사됨"; setTimeout(function(){ btn.textContent=t; },1200); }
    if(navigator.clipboard && navigator.clipboard.writeText){ navigator.clipboard.writeText(txt).then(flash, flash); }
    else { try{ var r=document.createRange(); r.selectNodeContents(el); var sel=window.getSelection(); sel.removeAllRanges(); sel.addRange(r); document.execCommand("copy"); }catch(_){ } flash(); }
  });
  if(state && state.selected){
    var sn=cy.getElementById(state.selected);
    if(sn && sn.length){ try{ onNodeTap(sn); }catch(e){} }
  }
})();
</script>
'''


def app_js_v2() -> str:
    return recolor(B.APP_JS) + "\n" + _V2_OVERRIDE


# ═════════════════════════════════════════════════════════════════════════════
# 5. 조립 + 기록
# ═════════════════════════════════════════════════════════════════════════════
def build_html() -> str:
    assert_glossary_complete()
    data_script = (
        "<script>\n"
        "var ELES=" + B.js(B.ELES) + ";\n"
        "var CUNITS=" + B.js(B.CUNITS) + ";\n"
        "var QINFO=" + B.js(B.QINFO) + ";\n"
        "var NODEINFO=" + B.js(B.NODEINFO) + ";\n"
        "var AXIS_STATES=" + B.js(B.AXIS_STATES) + ";\n"
        "var FAMILIES=" + B.js(B.FAMILIES) + ";\n"
        "var DEFERRED_VIEW=" + B.js(B.DEFERRED_VIEW) + ";\n"
        "var DT_STATS=" + B.js(B.STATS) + ";\n"
        "var DT_BANNER=" + B.js(B.BANNER) + ";\n"
        "var WIZARD=" + B.js(WIZARD) + ";\n"
        "var GLOSSARY=" + B.js(GLOSSARY) + ";\n"
        "var EASY=" + B.js(EASY) + ";\n"
        "</script>\n"
    )
    return page_head_v2() + "\n" + B.LIBS + "\n" + data_script + app_js_v2() + B.PAGE_TAIL


def main():
    html = build_html()
    out = B.ROOT / "render" / "index_v2.html"
    out.write_text(html, encoding="utf-8")
    kb = len(html.encode("utf-8")) / 1024.0
    print("[build_html_v2] wrote %s" % out)
    print("[build_html_v2] size = %.1f KB" % kb)
    print("[build_html_v2] glossary: axis=%d state=%d qcode=%d kind=%d layer=%d terminal=%d vocab=%d" % (
        len(GLOSSARY["axis"]), len(GLOSSARY["state"]), len(GLOSSARY["qcode"]),
        len(GLOSSARY["kind"]), len(GLOSSARY["layer"]), len(GLOSSARY["terminal"]), len(GLOSSARY["vocab"])))
    print("[build_html_v2] wizard: file_property=%s data_dependent=%d canon=%d qa_tokens=%d" % (
        WIZARD["file_property_c"], len(WIZARD["data_dependent_c"]), len(WIZARD["canon_order"]), len(WIZARD["qa_tokens"])))


if __name__ == "__main__":
    main()
