"""gap_annotator — unwired 구조를 [[GAP-37]] 사유로 기술 + 모호-wide 2옵션 제시(D-G2).

unwired finding은 라우팅하지 않는다(현 57-wired 백본에 대응 transform/route 없음).
"감지했으나 미배선([[GAP-37]])"으로 구조 증거만 기술한다.
subject-as-column wide의 *종류*(동일군 재측정 vs 별개 arm)가 구조만으로 불확정이면
silent 선택을 금하고(D-G2) 두 해석을 모두 surface한다 — 사용자 결정 대상.
"""
import re

_REANALYSIS = re.compile(r"(재산출|재분석|re-?anal|\(re\))", re.I)


def annotate_unwired(findings) -> list:
    """unwired finding → GAP-37 사유 엔트리."""
    return [{"feature": f.feature, "what": f.what,
             "structural_evidence": f.structural_evidence, "gap": "GAP-37"}
            for f in findings if not f.wired]


def surface_ambiguous_wide(structure: dict) -> list:
    """재산출/재분석 마커가 붙은 wide 컬럼 = 종류 불확정 → 두 해석 제시(D-G2).

    구조만으로 자동 판정하지 않는다 — interpretation_A/B를 모두 반환하고 선택은 사용자.
    """
    out = []
    for name, s in structure["per_sheet"].items():
        markers = []
        for row in s["sample"]:
            for v in row:
                if v and _REANALYSIS.search(v):
                    markers.append(v.strip())
        if markers:
            out.append({
                "feature": "wide-type",
                "sheet": name,
                "evidence": markers[:4],
                "interpretation_A": "동일 그룹의 재산출/재측정(replicate·reanalysis) → reconcile/dedupe 후 단일 시계열",
                "interpretation_B": "별개 arm/그룹(예: RLD vs 시험) → 분리 유지 + subject-wide→long PIVOT 개별 처리",
                "why": "재측정 vs 별개군이 구조만으로 불확정 — 자동 선택 시 silent 오류(D-G2). 사용자 결정 필요.",
            })
    return out
