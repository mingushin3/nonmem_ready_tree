# Phase 5b/7 정산 체크리스트 — OPEN GAP 백로그 정산 뷰 (living backlog)

> **목적:** slice를 더 쌓기 전 OPEN/잔여 GAP 백로그를 한눈에 파악해 Phase 전환(5→5b→6→7→8)을 예측 가능하게 한다.
> **위상:** `issues/provenance_gaps.md`(GAP 원장)에서 **파생한 뷰**다. 원장이 SSOT — 충돌 시 원장 우선. 본 파일은 OPEN/잔여 GAP만 (a)처리방침/(b)담당Phase/(c)작업성격으로 재배열한 정산 인덱스이며, GAP의 근거·cite-verify는 원장에 있다.
> **갱신:** slice/Phase 종료마다 갱신하는 **살아있는 백로그**(하단 [갱신 규약] 참조).

## Snapshot
- **기준 시점:** 2026-05-31 · Phase 5 **slice 5(PLACEBO_SUBJECT) 완료 후**.
- **테스트 baseline:** `python3 -m pytest tests/ -q` → **734 passed / 4 skipped / 1 xfailed**.
- **집계(총 27 GAP):** OPEN **21**(GAP-1~15, 17, 18, 19, 22, 23, 24) · RESOLVED-잔여 **5**(GAP-16, 21, 25, 26, 27) · RESOLVED-clean **1**(GAP-20, 백로그 제외).
- **비-GAP(상시 지침, 백로그 아님):** [PRINCIPLE] happy 입력=선행 출력 · [PRINCIPLE §6] PROPAGATE scope · [DECISIONS D1–D3].
- **공통 패턴:** 대다수가 *"단위테스트는 fixture 주입으로 green이나 chain/tree에서 드러나는"* 구조 항목 — 즉시 결함 아님, Phase별 정산 대상.

(c) 작업성격 범례: **배선**=orchestrator 코드(spec 무변경, by-design 외부입력) · **spec 변경**=c_units/q_codes 등 SSOT 수정(승인) · **신규 c**=새 c-unit · **설계**=decision-tree/D-S4 구조 결정 · **문서**=문서/라벨 정정 · **검증**=재측정/점검.

---

## ① Phase 5 — orchestrator 전체 통합 정산 (외부입력 주입 + chain 계약)
> "full sc→terminal run"(현재 slice-scoped) 진입 시 일괄 정산. 외부입력 GAP은 개별 slice가 아니라 **통합 시점에 외부 meta 주입 규약을 1회 설계**하면 동시 해소된다.

| GAP | 요지 | (a) 처리 방침 | (c) 작업 성격 |
|---|---|---|---|
| GAP-4 | A0 analysis_intent/endpoint_data_type 외부입력 | sc/external meta 주입; 미제공→AIC-MISSING→Q11 graceful | 배선(by-design) |
| GAP-6 | A1 study_integration/harmonization 외부입력 | 주입; 미제공→df study수 추론 | 배선(by-design) |
| GAP-7 | A3 time_policy 외부 + time_value 상류 컬럼 | 주입 + c0311(구현)→c0203/c0019 컬럼명 계약 점검 | 배선 + chain 점검 |
| GAP-9 | A2 study_design 외부 + fallback 8/10 미달 | 주입; (선택) A2 UNKNOWN+Q escape는 universe 변경 | 배선(+선택 spec) |
| GAP-10 | c0206 a0_state chain + occasion/event_row_state 외부 | A0≺A6 순서 보장 + 주입; a0_state 부재 경로면 STOP | 배선 + 순서 불변식 |
| GAP-11 | c0207 covariate_state 외부 + fallback 3/8 | 주입; POLICY/KEY-MISSING 미선언→Q07/Q13 silent 미발화 점검 | 배선(by-design) |
| GAP-12 | c0209 defect_state 외부 + fallback 3/13 | 주입 | 배선(by-design) |
| GAP-13 | c0210 file_format 외부 + fallback 1/8 + **A10 실행 위치** | 주입 + **A10 front vs chain-끝 실행 위치 결정** | 배선 + **설계 재검토** |
| GAP-14(#5) | c0204 dose_regimen / c0208 study_type 외부입력 | orchestrator 주입(라벨 매핑은 ③) | 배선(by-design) |
| GAP-22 | c0015 a4_state→Q14가 req_det(c0010) 밖 c0204 키 의존 | axis(c0200–c0210) ≺ L-1→L-2 transform 순서 불변식 보장 | 배선(순서 불변식) |
| GAP-1 | cmt_map flat(c0208) vs nested(c0013) | meta 계약 통일(orchestrator 또는 fixture/spec snippet 정정) | 계약 정정(코드/spec) |
| GAP-2 | dose_interval 생산자 부재(c0015→c0016) | c0015가 등간격 압축 시 dose_interval emit | **spec 변경**(output_schema_delta)·승인 |
| GAP-3 | baseline/tv_covariates 리스트 생산자 부재 | 별도 생산자(c0207 확장은 GAP-11서 불가 확정) | **spec 변경/신규 producer**·승인 |
| GAP-15 | c0020/c0021 BLQ chain(blq_detected/lloq_value←c0306 미구현, blq_policy 외부) | c0306→c0020/c0021 cross-layer 순서 + blq_policy 주입 + c0020→c0021 순서 | 배선 + (c0306 **신규 c**) |
| GAP-18 | c0019 time_value 생산자(c0311 상류, GAP-7 동형) | c0311(구현)→c0019 컬럼명(time_value) 계약 점검 | chain 점검(코드) |

## ② Phase 7 — decision-tree D-S4 (conditional edge · 고립 terminal · commutativity)
> 라우팅 scope-out·fail-branch는 best-strand에 없으므로 tree 조립 시 conditional edge로 명시 재구성. **고립 Q-terminal 0 / 골격 무모순**이 Phase 7 종료 게이트.

| GAP | 요지 | (a) 처리 방침 | (c) 작업 성격 |
|---|---|---|---|
| GAP-5 | c0204 Q04/INVALID 라우팅 scope 밖 | 하류 ROUTE c/conditional edge로 Q04·INVALID terminal 연결; (선택) Q04 q_code SM 연결 | 설계 + 선택 spec(q_code) |
| GAP-8 | c0205 ABSENT→INVALID scope 밖 | 하류 ROUTE c/conditional edge로 INVALID terminal 연결 | 설계(ROUTE/edge) |
| GAP-10 | c0206 Q03 교차축 conditional edge | Q03 고립 terminal 방지(c0206 Q03 emit을 conditional edge로) | 설계(D-S4) |
| GAP-12 | c0209 IRRECONCILABLE→INVALID + Q06/Q15D | conditional edge + INVALID terminal 연결 | 설계(D-S4) |
| GAP-13 | c0210 NON-TABULAR→UNSUPPORTED/CORRUPTED→INVALID | conditional edge + terminal 연결(+A10 위치 ①와 연동) | 설계(D-S4) |
| GAP-26 | c0019/c0311/c0315/c0213 fail→Q conditional edge(strand 0) | fail-branch conditional edge 재구성 + 고립 Q-terminal 점검 | 설계(D-S4) · RESOLVED 이월 |
| GAP-27(B) | FORMAT↔TIMEZONE 비-commutative 가능성(c0311→numeric이 tz 토큰 소실) | canonical order(D-S2) 결합 chain 정합·순서 재검토 | **설계 재검토** · RESOLVED 이월 |

## ③ Phase 7/8 — 노드 라벨 매핑 + render
| GAP | 요지 | (a) 처리 방침 | (b) | (c) 작업 성격 |
|---|---|---|---|---|
| GAP-14 | axis srp_intent NOUN ↔ axis 개념 체계 불일치(c0200–c0210) | raw srp_intent 대신 axis 개념 표시명 사전 매핑(spec frozen) | 7/8 | 문서/렌더 매핑 |
| GAP-21(잔여) | plain-melt snippet ↔ refined 구현 라벨 주의 | HTML snippet 렌더 시 불일치 주의(GAP-14 동류) | 7/8 | 렌더 주의 · 잔여 |
| GAP-25 | 렌더 perf 게이트(collapse-by-default PASS, Lock 6 유지) | decision_tree 생성 후 실 axis-state(101)로 재측정; collapse/cull/증분 필수 | 8(+7) | 검증·재측정 · 대기 |

## ④ Phase 5b 문서정산 · 신규 c/설계 · spec 승인대기 (cross-cutting)
| GAP | 요지 | (a) 처리 방침 | (b) | (c) 작업 성격 |
|---|---|---|---|---|
| GAP-23 | CLAUDE.md layout(refs//spec/) ↔ 실제 root 위치 drift | CLAUDE.md 정정 또는 파일 이동(+verify_phase3/generate_sc 경로 동반) | **Phase 5b** | 문서 정정(또는 파일 이동)·승인 |
| GAP-24 | c0341 cross-subject ffill bleed(latent, xfail 고정) | c0018 후 하류 subject-boundary VERIFY cut-vertex 신설 + Q-route(TBD) | Phase 5/7 | **신규 c** + 설계 + Q 결정 |
| GAP-16 | c0121 req_det 필드 respec(RESOLVED, 잔여) | req_det c0207→c0381 또는 dual-detector 표기(이중 의존); c0121.py docstring stale 동반 | spec 정산 | **spec 변경**·승인 |
| GAP-21(B) | covariate_columns 생산자 부재(df fallback 잔여) | GAP-3 종속 — 생산자 신설 시 동반 해소 | Phase 5 | spec/신규 · GAP-3 연동 |
| GAP-17 | c0140 TIME 시점 + groupby 키 불일치 | 구현 graceful fallback 적용됨(DECISION-D3); spec snippet TIME→time_value 정정만 잔여 | spec 정산 | spec snippet 정정(선택, 이미 impl 우선) |
| GAP-19 | c0022 fillna median ↔ IMPUTE 금지 override(확정) | 구현 override 유지(사용자 ★★★); Phase 6 alias 시 c0022/c0140 동일 처리 확인 | Phase 6 | 인지/no-action(선택 spec snippet) |

---

## Phase 전환 예측
- **추가 slice는 ①을 늘리지 않음** — 외부입력 GAP은 개별 slice가 아니라 **full-orchestrator 통합 시점에 1회 일괄 정산**(외부 meta 주입 규약 설계).
- **Phase 7이 ②(7건)를 흡수** — 라우팅 scope·Q03·commutativity = D-S4 핵심. 고립 Q-terminal 0 / 골격 무모순이 종료 게이트.
- **자연스러운 순서:** slice 누적 종료 → **Phase 5 full-integration(① 일괄) → 5b(GAP-23) → 6(GAP-19/20) → 7(②③) → 8(③)**.
- **신규 작업 유발은 소수:** GAP-24(신규 VERIFY c), GAP-2/3/15(생산자 emit) — 나머지는 배선/매핑/설계.
- **spec 승인 묶음**(slice 누적과 무관, 사용자 결정 시): GAP-2/3(생산자), GAP-5(Q04), GAP-16(req_det), GAP-9(A2 escape·선택).

---

## 갱신 규약 (living backlog)
slice/Phase 종료 시 본 파일을 다음 순서로 갱신한다(원장 `provenance_gaps.md`가 SSOT):
1. 해당 작업으로 **resolved된 GAP** 행을 제거하거나 "→ RESOLVED(Phase/slice)"로 표기.
2. `provenance_gaps.md`의 status 변경과 **동기화**(본 뷰가 원장을 앞서지 않도록).
3. **집계**(OPEN/잔여/clean 수)와 Snapshot(날짜·테스트수) **재산출**.
4. 신규 GAP이 원장에 추가되면 해당 bucket(①~④)에 행 추가.
5. 충돌·불확실 시 원장을 신뢰하고 본 파일을 정정(반대 금지).

> 이력: 2026-05-31 최초 작성(slice 4 후, OPEN 21 + 잔여 5). · 2026-05-31 slice 5(PLACEBO_SUBJECT) 후 갱신: 자기완결 detect+classify(c0392/c0393), **GAP 무변동**(신규/종결 0 — c0393 vacuous-postcond는 GAP-27 패턴 재사용, 하류 transform·활성화 없음, AMT=0↔EVID 상호작용은 미배선 future-c 소관으로 out-of-scope). 집계 불변(OPEN 21 + 잔여 5 + clean 1). baseline 704→734 passed.
