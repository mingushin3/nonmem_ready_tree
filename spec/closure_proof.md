# Phase 3.9 — c-set Closure Proof

> **Date:** 2026-05-27
> **Verifier:** Claude Code (closure verifier role)
> **Inputs:** `spec/c_units.json` (122 entries), `spec/strands.json` (5000 entries)
> **Cross-ref:** `spec/strands_stats.md` (Phase 3.5 output)
> **Method:** Independent programmatic verification (`_verify_closure.py`), not relying on Phase 3.5 results

---

## INV-1: c_id Membership

**Predicate:** ∀ s ∈ strands.json, ∀ c ∈ s.c_sequence : c ∈ C_all

| Metric | Value |
|--------|-------|
| C_all (c_units.json) | 122 |
| C_used (unique c_ids in strands) | 119 |
| Orphans (in strands ∉ c_units) | 0 |

**Result: PASS**

Every c_id referenced by any strand's c_sequence exists as a defined entry in c_units.json.

---

## INV-2: Adjacent Predicate Implication

**Predicate:** ∀ s ∈ strands.json, ∀ adjacent pair (c_i, c_{i+1}) in s.c_sequence :
  post(c_i) ∪ cumulative_state(s, 0..i) ⊇ pre(c_{i+1})

### 2a. `_passed` variable satisfaction

For every c whose `precondition_predicate` references `cXXXX_passed`, the c with c_id=cXXXX appears strictly before it in the same strand's c_sequence.

| Metric | Value |
|--------|-------|
| Unique adjacent pairs | 529 |
| `_passed` reference violations | 0 |

### 2b. Structural column availability

Adjacent pairs were analyzed for column-existence preconditions (`'COL' in df.columns`). No pair requires a column that the cumulative c_sequence up to that point cannot provide (output_schema_delta trace).

**Result: PASS**

---

## INV-3: Dead C-units

**Predicate:** C_dead = C_all \ C_used

| Metric | Value |
|--------|-------|
| C_dead count | 3 |
| Matches Phase 3.5 report | YES |

### Dead C-units Detail

| c_id | c_name_ko | kind | layer_pair | requires_detection_by | can_route_to_q | Reason for dead status |
|------|-----------|------|-----------|----------------------|----------------|----------------------|
| c0042 | 불변 조건 위반 라우팅 | route | L-1→L-2 | c0041 | Q01, Q04, Q08, Q09 | Triggered only on c0041 (VERIFY CROSS_COLUMN_INVARIANT) fail. All 5000 best-strands pass c0041 — fail-path never traversed in pass-only strand set. |
| c0043 | 스키마 실패 라우팅 | route | L-1→L-2 | c0001 | Q11, Q15X | Triggered only on c0001 (VERIFY COLUMN_SCHEMA) fail. All 5000 best-strands pass c0001 or route to Q earlier — fail-path never traversed. |
| c0333 | 단위 실패 라우팅 (L-4) | route | L-4→L-5 | c0330 | Q10 | Q10 routing occurs at c0170 (L-2→L-3) with higher priority per derive_terminal. c0333 is structurally redundant for best-strand routing. |

### Structural significance

All 3 dead c-units are **route** kind (cost=0) handling **fail-path** branches. Per D-S4 (conditional-edge reconstruction), these c-units' `can_route_to_q` fields are needed to generate conditional edges in the decision tree (Phase 7 step 2.5), even though best-strands (pass-only) never traverse them.

### C_dead disposition options (사용자 결정 필요)

| c_id | Option A: Remove | Option B: Add sc | Option C: Keep as-is |
|------|------------------|------------------|---------------------|
| c0042 | Phase 2 re-entry: spec에서 삭제. Q01/Q04/Q08/Q09의 conditional edge 하나 감소. | Phase 3 re-entry: c0041 fail sc 추가. 기존 5000 sc 외 별도 fail-path 시나리오. | **D-S4 구조상 필요.** fail-path conditional edge 원천. strand에서 dead이나 tree에서는 live. |
| c0043 | Phase 2 re-entry: spec에서 삭제. Q11/Q15X의 conditional edge 하나 감소. | Phase 3 re-entry: c0001 fail sc 추가. schema 결함 시나리오. | **D-S4 구조상 필요.** schema 실패 시 Q-code routing의 유일한 경로. |
| c0333 | Phase 2 re-entry: spec에서 삭제. Q10 routing은 c0170이 담당. | Phase 3 re-entry: c0170보다 c0333이 먼저 도달하는 sc 추가. | c0170이 동일 Q10을 routing하므로 실제 중복. 단, layer 계층이 다름(L-4 vs L-2). |

---

## INV-4: D-S1 Detection-Mandatory

**Predicate:** ∀ s ∈ strands.json, ∀ c ∈ s.c_sequence where c.kind ∈ {transform, route} ∧ c.requires_detection_by ≠ null :
  c.requires_detection_by ∈ s.c_sequence[0 : index(c)]

| Metric | Value |
|--------|-------|
| transform/route c with non-null rdb | 62 |
| Strands checked | 5000 |
| Violations | 0 |

Every transform and route c-unit with a `requires_detection_by` dependency has that dependency satisfied by a preceding c in the same strand's c_sequence.

**Result: PASS**

---

## Cross-check with Phase 3.5 (strands_stats.md)

| Phase 3.5 reported | Phase 3.9 independent result | Match |
|--------------------|------------------------------|-------|
| D-S1 violations: 0 | INV-4 violations: 0 | YES |
| D-S2 violations: 0 | (D-S2 is ordering, not in 3.9 scope) | N/A |
| C_dead: 3 {c0042, c0043, c0333} | INV-3 C_dead: 3 {c0042, c0043, c0333} | YES |
| C_used: 119, C_all: 122 | INV-1 C_used: 119, C_all: 122 | YES |

No discrepancies found.

---

## Summary Verdict

| Invariant | Result |
|-----------|--------|
| INV-1: c_id membership | **PASS** |
| INV-2: Adjacent predicate implication | **PASS** |
| INV-3: Dead c-units | **3 reported** (사용자 결정 대기) |
| INV-4: D-S1 detection-mandatory | **PASS** |

### **CLOSURE_PASS**

c-unit set과 strand set은 closed, consistent system을 구성한다.

---

## 다음 Phase 전 사용자 확인 필요 사항

1. **C_dead 3건 처분:** c0042, c0043, c0333 각각에 대해 Option A/B/C 중 선택.
   - 권장: c0042, c0043은 **Option C (Keep)** — D-S4 conditional edge 원천으로 Phase 7에서 필요.
   - 권장: c0333은 **Option A (Remove) 또는 C (Keep)** — c0170과 중복이나 layer 계층이 다르므로 보수적으로 Keep 가능.
2. 결정 후 Phase 4 (TDD 구현) 진행 가능.
