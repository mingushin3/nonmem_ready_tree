"""ROUTE AMT — A4 실패 라우팅

srp_intent: ROUTE AMT
c_name_ko: A4 실패 라우팅
kind: route  (cost 0; a4_state fail state → Q-terminal 라우팅)

postcondition_predicate:
    routing_decision in ['Q08', 'Q14', 'INVALID']

precondition_predicate:
    meta.get('a4_state') in ['MISSING-NO-POLICY', 'ADDL-ACTUAL-CONFLICT', 'UNRECOVERABLE']

라우팅 매핑(★ SSOT = strands.json + q_codes.json):
    MISSING-NO-POLICY     → Q08  (QUARANTINE; strands 203)
    ADDL-ACTUAL-CONFLICT  → Q14  (QUARANTINE; strands 191)
    UNRECOVERABLE         → INVALID(q_code=None; default; strands 174)
    그 외(default)        → INVALID(q_code=None)
★ GAP-31: strands.json은 INFUSION-STOP-RESTART → Q04(168 strand)로 라우팅하나, Q04 ∉ 본 c의
  postcond ['Q08','Q14','INVALID'](또한 precond·can_route_to_q에도 미선언)이다. c0251(ROUTE
  TIME_FORMAT)이 산문 'UNRECOVERABLE→INVALID'를 무시하고 SSOT Q12를 채택할 수 있었던 것은
  Q12 ∈ postcond였기 때문 — 여기선 Q04 ∉ postcond이라 SSOT 채택 시 postcond(verbatim, 1글자 변경
  금지)를 위반한다. 따라서 postcond-faithful하게 INFUSION-STOP-RESTART는 default→INVALID로
  라우팅한다(c0253 ABSENT→INVALID 선례 동형). SSOT(Q04)↔postcond divergence는 Phase 7 D-S4
  conditional-edge 재구성으로 흡수한다(issues/provenance_gaps.md GAP-31, GAP-28 동형).
can_route_to_q=[Q08,Q14] ⊆ 실제 라우팅 {Q08,Q14,INVALID}(Q15D 없음); Q04는 미선언 divergence(GAP-31).
requires_detection_by=c0204 (D-S1: a4_state는 c0204(verify_amt)가 생산).
slice 8 (Batch A) — c0251/c0253 패턴 동형.
"""

import pandas as pd

# a4 fail state -> Q-code (q_codes / strands.json SSOT 정합; postcond ['Q08','Q14','INVALID'] 준수)
_A4_FAIL_TO_Q = {
    "MISSING-NO-POLICY": "Q08",
    "ADDL-ACTUAL-CONFLICT": "Q14",
    # UNRECOVERABLE / INFUSION-STOP-RESTART(GAP-31) / 그 외 → INVALID (default)
}


def route_amt(df: pd.DataFrame, meta: dict) -> dict:
    a4 = meta.get("a4_state")
    routing_decision = _A4_FAIL_TO_Q.get(a4, "INVALID")
    if routing_decision in ("Q08", "Q14"):
        terminal, q_code = "QUARANTINE", routing_decision
    else:
        terminal, q_code = "INVALID", None
    return {
        "routing_decision": routing_decision,
        "terminal": terminal,
        "q_code": q_code,
    }
