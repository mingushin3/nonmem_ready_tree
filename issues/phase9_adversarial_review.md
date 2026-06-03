# Phase 9 — Adversarial Review (mode: skeptical) — DoD/Lock 충족 매트릭스 + 한계 정직 보고

> 기록: 2026-06-03. **mode: skeptical** — 산출물이 옳다고 가정하지 않고 weakness/숨은 GAP를 falsifiable하게 발굴.
> 역할 분리: 본 doc = "무엇을 증명했는지 설명" · `tests/test_phase9_adversarial.py`(+12) = "참 증명"(자기검증 대신 pytest, Hallucination 차단 #6 / DoD #2).
> **REPORT-ONLY**: spec/src/render 무수정. 발견은 GAP로 기록([[GAP-36]] 신규).
> baseline: `python3 -m pytest tests/ -q` → **974 passed / 4 skipped / 1 xfailed** (962 + Phase 9 12). git HEAD=199ec47(Phase 8/8b).
> 재현: `python3 tests/test_phase9_adversarial.py`(수치 매트릭스) · `python3 -m pytest tests/test_phase9_adversarial.py -q`.

## 0. 결론 요약 (TL;DR)

- **기계화 적대 cross-check 12/12 PASS** (P9-1..12 — SSOT 무결·D-S1·D-S4 wired·scope_out 0·banner build-time·렌더 정직·C1 경계).
- **기존 35 GAP ledger가 한계를 거의 전부 정직 포착**: c0040 placeholder([[GAP-34]] deferred)·235/439 2축([[GAP-35]])·끊김 정상([[GAP-35]]) 모두 기기록.
- **미기록 결손 1건 발견** → **[[GAP-36]]**: 문서화된 C_dead {c0042/c0043/c0333}의 closure_proof "tree-live" 처분이 57-wired decision_tree에서 미실현 + DoD#3 **C1 = 119/122 bound**가 living ledger 미기록. **②latent(즉시 결함 아님, 배선 시 해소)·non-critical.**
- **∴ 숨은(미기록) GAP = 1 발견·기록 / critical = 0.** 적대 sweep이 작동함을 입증(무서운 "anchors.json MISSING" 오경보가 "root 위치 = 기존 GAP-23"로 환원된 것도 동일).
- **완성도**: 현 **57-wired/235-oracle/88-realized** 경계 내 DoD·Lock 충족·SSOT 무결·렌더 정직 = 높음. 전체(5000/122c) closure는 ①·Batch C/D/E 필요(결함 아닌 정직히 경계된 부분 완성).

---

## §A. DoD #1–#8 충족 매트릭스

| # | DoD 항목 | 판정 | falsifiable 증거 |
|---|---|---|---|
| 1 | Pilot RECOMMEND | **PASS** | `spec/pilot_validation.md:496` "RECOMMEND: 본 build 진행"; clean-route 7/7 (100%) |
| 2 | Test green | **PASS** | `pytest tests/ -q` 974 passed / 4 skipped(C3 N/A) / 1 xfailed([[GAP-24]] cross-subject bleed, strict=False·문서화) |
| 3·C1 | 모든 c ≥1 strand or cond-incoming | **BOUNDED 119/122** | dead c = 문서화 C_dead {c0042,c0043,c0333}(closure_proof INV-3·strands_stats §6). 미기록 dead 0(`test_p9_11`). 3 예외 = [[GAP-36]] ②latent |
| 3·C2 | 모든 edge traverse | **PASS(wired)** | `tests/test_coverage.py` C2(intra-family edge + exit, dead-end 0) |
| 3·C3 | 모든 Q-code trigger | **BOUNDED** | exercised Q 13 trigger(strands.json Q01..Q15D 실측) · static 2(Q05/Q10)+unreached 4(Q15A/B/C/X) **문서화**(`test_p9_8`, q_partition) |
| 3·C4 | 인접 c predicate implication | **PASS** | `spec/closure_proof.md` **INV-2 PASS**(529 인접쌍, 미제공 컬럼 0) + `tests/test_strands.py::test_*_precedes_fix_adjacent` |
| 3·C5 | actual_cost ≤ best+ε | **PASS** | `tests/test_decision_tree.py::test_cost_invariance_all_5000`(5000 strand total_cost==Σc.cost) |
| 4·D-S3 | 모든 strand N0–N7 골격 통과 | **PASS** | `tests/test_skeleton.py`(22; mess L-4→L-5가 backbone 선행, 6 family + Batch B) |
| 4·D-S4 | can_route_to_q→cond edge·고립 Q-terminal 0 | **PASS(wired)** | 배선 c 누락 edge 0(`test_p9_2`) · exercised Q 고립 0(`test_p9_3`) · unreached Q router 미배선 documented(`test_p9_8`) |
| 5 | Adversarial critical 0 ×2 cycle 연속 | **IN-PROGRESS 1/2** | 본 cycle critical 0([[GAP-36]]=②latent non-critical). **2번째 연속 cycle 필요**(다음 슬라이스 후 재sweep 권고) |
| 6 | HTML(fit/click/highlight/persist/perf/bundle) | **PASS** (bundle facet N/A) | [[GAP-25]] perf dagre 94ms/total 281ms ≪10s · `tests/test_render.py`(25). bundles=0(DEFER [[GAP-27]]B)라 bundle-click facet N/A·collapse는 axis-state cell |
| 7 | UAT "의도대로다" | **PASS** | [[GAP-35]] Phase 8b 사용자 Chrome 실물 UAT(끊김 판정=정상·시각 명료성·recover edge 반영) |
| 8 | [AMBIGUOUS] 0개 | **PASS** | 리터럴 `[AMBIGUOUS:` 미해결 태그 0(spec self-check "잔존 0개? Yes" — L0/layers/vocabulary) |

**요약:** 8항 중 **PASS 6 · BOUNDED 1(#3 일부, 경계 문서화) · IN-PROGRESS 1(#5 2nd cycle)**. 미충족 0(경계는 전부 정직 기록).

---

## §B. Lock 1–7 충족 매트릭스

| Lock | 내용 | 판정 | 증거 |
|---|---|---|---|
| 1 | sc 열거 symbolic·stratified·seed 42 | **PASS** | `spec/starting_conditions.json`(5000 sc, mess_profile dict, seed 42); strands.json 5000 |
| 2 | c granularity (SRP, 1 verb/intent) | **PASS** | 122 c, srp_intent 전부 `VERB NOUN` 대문자형(vocab 위반 0) |
| 3 | Best-path 제약우선·cost 후순위 | **PASS** | strands.json oracle(feasibility filter + layered Dijkstra) · `test_cost_invariance_all_5000` · constraint>cost 불변 |
| 4 | Semantic equivalence(보수적) | **PASS** | 동치 기준 정의·보수 적용; SSOT cross-check서 srp_intent/schema-delta 모순 0(중복 alias 결함 미발견) |
| 5 | Convergence(skeleton+suffix-tree) | **PASS** (bundle DEFER) | 골격 N0–N7 고정(D-S3, `test_skeleton`); 다발 압축 bundles=0 **명시 deferred**([[GAP-27]]B, honest) |
| 6 | HTML stack(Cytoscape+dagre·단일·localStorage·외부image 0) | **PASS** | inline cytoscape 3.30.2/dagre 0.8.5, 단일 815KB, `pmx_dt_state`, `<img>` 0(`test_render`) |
| 7 | Downstream highlight(#FFD700/5px·#FFF8B0/3px) | **PASS** | Lock7 hue frozen 유지(GAP-35 cite-verify); recover edge는 union 제외(`flowNeighborhood`); `test_render` |

**요약:** Lock 7/7 준수. 유일 경계 = Lock 5 다발 압축 deferred(bundles=0, [[GAP-27]]B 가시 마커 — 미준수 아닌 명시 이월).

---

## §C. 적대적 점검 결과 (기계화 12 + candidate 4 + 발주 concern a–e)

### C-1. 기계화 cross-SSOT 불변식 (`tests/test_phase9_adversarial.py`, 12/12 PASS)

| ID | 불변식 | 실측 | 판정 |
|---|---|---|---|
| P9-1 | D-S1 dangling requires_detection_by | null_tf 0 / dangling 0 | PASS |
| P9-2 | D-S4 wired can_route_to_q→cond edge | 누락 0 | PASS |
| P9-3 | exercised Q 고립 | 0 | PASS |
| P9-4 | recover_to_c_id 타깃 존재 | dangling 0 | PASS |
| P9-5 | strand c_id/q_code 무결 + QUARANTINE⟺q_code | bad 0 / coupling 위반 0 | PASS |
| P9-6 | can_route_to_q ⊆ q_codes ⊆ anchors(G1) | 위반 0 | PASS |
| P9-7 | scope_out 0(GAP-28 결정 C) | edges 0 / strands 0 | PASS |
| P9-8 | unreached Q documented + router 미배선 | Q15A/B/C/X 전부 doc·router 0 | PASS |
| P9-9 | anchors root 위치(GAP-23) | root=True, spec/=False | PASS |
| P9-10 | banner build-time 재계산 == index.html | 일치 | PASS |
| P9-11 | C1 dead c == 문서화 C_dead | {c0042,c0043,c0333}, 미기록 dead 0 | PASS |
| P9-12 | recover 미배선 타깃 = 알려진 omit | {c0330,c0368,c0499} | PASS |

### C-2. candidate findings 처분

| 후보 | 내용 | 처분 |
|---|---|---|
| A | c0040(미배선 verify) fail_route_to='해당 invariant에 따른 Q-code' 자연어 placeholder | **기문서화** — [[GAP-34]]:548 deferred "c0040(명시 이월)". ②latent(배선 시 구체 Q 필요). 신규 아님 |
| B | 235(oracle) vs 439(orchestrator) 2축 라벨 | **기문서화** — [[GAP-35]]:564 명시(banner 235만·439 "배너 미포함 별도"). render 정직. checklist는 §아래 라벨 보강 |
| C | `test_termination_legend_present` 숫자 아닌 label만 검사 | **benign** — 숫자는 `test_boundary_banner_numbers`가 build-time 검증(중복 커버). GAP 아님 |
| D | pass_route_to "next"/"next axis" 비정형 토큰(c0210/c0214) | **benign** — PASS-분기 순차진행 의미(fail 분기 아님), 라우팅 주장 미생성. GAP 아님 |
| **★신규** | C_dead {c0042/c0043/c0333} tree-live 미실현 + C1 119/122 bound가 **living ledger 미기록** | **[[GAP-36]] 기록**(②latent non-critical) — C-3 참조 |

### C-3. 발주 concern (a)–(e) 정산

- **(a) SSOT 교차정합**: c_units↔strands↔q_codes↔anchors↔decision_tree **모순 0** — 선언 Q↔실제 라우팅(P9-2/6), terminal 도달성(P9-3/8 + INVALID 315 incoming≥1), 고립 노드(unreached Q만=의도), recover_to_c_id 타깃 존재(P9-4). **PASS.**
- **(b) ledger 완전성**: RESOLVED 16건(GAP-5/8/12/15/16/20/21/25/26/27/28/29/31/33/34/35) 재검 — 잔여 기록은 대체로 정확. 단 **C_dead/C1 bound 1건 미기록** 발견 → GAP-36. **PASS(+1 보정).**
- **(c) 렌더 정직성**: banner 12수치 build-time 재계산 일치(P9-10) · synthetic/recover/deferred/terminal 4종 ekind·스타일 분리 · recover wired+reachable만(미배선 c0330/c0368/c0499 omit, P9-12) · 끊김=구조그래프 아티팩트(GAP-35). **라우팅 주장과 혼동 0. PASS.**
- **(d) 미배선 영역 노출**: 미배선 c 62(banner)·① 미실현(realized 88)·UNREACHED-Q 4·static Q 2·**orphan C_dead 3(GAP-36 신규 가시화)** 모두 한계로 노출. **은폐 0(단 orphan 3은 banner 62 외 — GAP-36 권고).**
- **(e) 2축 수치 정합**: 완주 **439(orchestrator runtime)** vs **235(oracle, AUTO5+REPAIR230)** — render는 235만(검증가능), 439는 [[GAP-35]]:564 별 축 명시. checklist line 10 "완주 439"에 oracle-235 inline 라벨 보강(본 Phase 9서 갱신). **혼동 없이 구분 기록. PASS.**

---

## §D. 숨은 GAP 입증 (어떤 검증이 통과했는가)

**주장:** 현 산출물에 *미기록* 모순/결손은 (아래 보정 후) 0. 근거 = 다음 검증 전부 통과(falsifiable, 재현가능):

1. 기계화 12 불변식 PASS(`tests/test_phase9_adversarial.py`, C-1 표) — 회귀방지로 영구 고정.
2. 기존 test 962 green 유지(SSOT/엔진/렌더 무모순).
3. SSOT 5파일 교차참조 dangling 0(P9-1/4/5/6).
4. "anchors.json MISSING" 오경보 → root 위치·기존 GAP-23로 환원(P9-9).
5. candidate A/B/C/D → 기문서화 또는 benign(C-2).

**보정(정직):** 위 sweep이 **1건 미기록 결손**을 적출 → **[[GAP-36]]** 기록. 따라서 정확한 진술은:
> **"기계화 적대점검 12/12 PASS, candidate 4건 무해/기문서화. 단 1건(C_dead/C1 bound, ②latent non-critical)이 미기록이어서 GAP-36으로 편입. 편입 후 미기록 모순 0 · critical 0."**

이는 "별 문제 없음"(PROMPTS 금지)이 아니라, **적대 sweep이 실제로 1건을 잡아 기록**한 정직한 결과다.

---

## §E. 한계 정직 보고 — 무엇을 하고, 무엇을 안 하는가

현 산출물은 **결함이 아니라 정직히 경계된 부분 완성**이다. 각 한계의 문서화 위치:

| 한계(무엇을 안 함) | 수치 | 문서화 위치(정직성) |
|---|---|---|
| orchestrator 배선 범위 | **57/122 c wired** | banner "57-wired" · checklist ① · REGISTRY(src.orchestrator) |
| orchestrator 완주(runtime) | **439/5000** | checklist:10(+본 Phase 9 oracle-235 라벨) · [[GAP-30]] |
| oracle 완주(strands.json) | **235/5000**(AUTO5+REPAIR230) | banner "완주 235" · [[GAP-35]]:564 |
| ① 런타임 실현 | **realized 88/439** | banner "별도"(미포함) · checklist ①:57–59 · [[GAP-30]] |
| 미배선 c(strand 등장) | **62** | banner "미배선 c 62" · checklist:10 |
| **orphan C_dead(strand 미등장)** | **3 {c0042/c0043/c0333}** | closure_proof INV-3·strands_stats §6 · **[[GAP-36]] 신규**(banner 미표기→권고) |
| 미실현 Q(static) | **2 {Q05,Q10}** | banner "미실현 Q 2" · q_partition.static_no_strand |
| unreached Q(router 미배선) | **4 {Q15A/B/C/X}** | banner deferred · q_partition.unreached · `deferred.unreached_q`(per-Q trigger) |
| scope_out | **0** | [[GAP-28]] 결정 C RESOLVE(P9-7) |
| 다발 압축 | **bundles 0** | [[GAP-27]]B 가시 deferred 마커 |

**무엇을 하는가(정직):** ① 5000 oracle best-strand 도출(constraint-first Dijkstra) · ② 57-wired c로 orchestrator 부분 실행(완주 439, realized 88) · ③ 결정 tree 골격(node 100·conditional 52·terminal 315·scope_out 0)을 단일 interactive HTML로 렌더(build-time 검증가능 banner) · ④ 모든 한계를 banner/ledger에 노출.

**핵심:** "oracle 할당 ≠ wired 실현" 2축을 혼동하지 않음 — oracle이 미실현/미도달 Q(Q05/Q10/Q15A/B/C/X)로 보낸 **152 strand**은 QUARANTINE(사람개입)으로 정직 집계되되, 그 Q-terminal은 wired 미실현으로 표시(P9 매트릭스 [경계 정직] 라인).

---

## §F. 완성도 평가

- **현 경계 내 품질(57-wired/235-oracle/88-realized):** **높음.** DoD 6 PASS+1 BOUNDED(문서화)+1 in-progress · Lock 7/7 · SSOT 무결(12 불변식) · 렌더 정직(banner build-time) · 미기록 결손 1(→기록).
- **전체(5000/122c) 대비 진척(정직 지표):**
  - wired c **57/122 = 47%**
  - orchestrator 완주 **439/5000 = 8.8%** · realized **88/5000 = 1.8%**
  - oracle 완주 **235/5000 = 4.7%** (QUARANTINE 3380 = 사람개입 정상)
  - exercised Q **13/19** (static 2 + unreached 4)
  - decision tree 층(57-wired conditional/terminal-routing): **완전**(scope_out 0)
- **종합 등급:** **A− (within-scope) / 부분 완성(전체).** 결함 0(critical), 한계 전부 정직 문서화. 전체 closure는 신규 구현 잔여(아래 §G).

---

## §G. 다음 판정 — ① / Batch C·D·E 필요성

| 작업 | full DoD 필요성 | 무엇을 해소 | 규모 |
|---|---|---|---|
| **① orchestrator 전체 통합**(외부 meta 주입 규약) | **필요** | realized 88→full(C3 런타임 실현), 완주 439 실현화 | full-orchestrator 1회 일괄(checklist ①) |
| **Batch C/D/E**(L-1→L-2 4 + L-2→L-3 12 = 16 upstream c 신규 구현) | **필요** | C1 122/122([[GAP-36]] 해소·미배선 62→감소)·완주 439→467 | co-dependent 꼬리, ~6–7 슬라이스([[GAP-30]]) |
| **mess 46c**(L-4→L-5) | **필요** | 467→5000 · c0333 tree-live | 별개 후속 |
| **Phase 9 2nd cycle** | **필요(DoD#5)** | critical 0 ×2 연속 충족 | 다음 슬라이스 후 재sweep |

**판정:** ①·C·D·E 모두 **full DoD엔 필요**하나, 현 산출물은 그 경계를 **정직·정합하게** 문서화함(결함 아님). 권고 순서 = `column_path_implementation_backlog.md`(Batch C/D/E) → ① full-integration → mess. 각 별도 Phase-5-연속 슬라이스. closure_proof C_dead 처분(Option A/B/C)은 Batch E 배선과 함께 사용자 결정.

**Phase 9 자체:** critical 0(cycle 1). **STOP — 자동 진행 금지. 다음 Phase 발주 대기.**

---

## 부록 — 재현 명령

```
python3 tests/test_phase9_adversarial.py          # 12 불변식 수치 매트릭스
python3 -m pytest tests/test_phase9_adversarial.py -q   # 12 passed
python3 -m pytest tests/ -q                        # 974 passed / 4 skipped / 1 xfailed
```
신규 GAP: [[GAP-36]](issues/provenance_gaps.md) · 정산: issues/phase_settlement_checklist.md(Phase 9 행).
