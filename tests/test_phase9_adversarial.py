"""Phase 9 — 적대적 검증: 교차-SSOT 불변식 durable guard ("숨은 GAP 0" 회귀방지).

PROMPTS Phase 9(mode: skeptical) + DoD/Lock + 발주 적대점검을, 자기검증 대신 pytest로 고정한다
(Hallucination 차단 #6 / DoD #2). test = "참 증명", issues/phase9_adversarial_review.md = "무엇을
증명했는지 설명"(역할 분리). 각 test는 wired scope(orchestrator REGISTRY=57) 내 무모순을 검증하고,
미배선 tail은 "현재 경계의 정직한 미구현"으로 documented됨을 확인한다(은폐 0).

검증 대상(번호=review doc §C 항목):
  P9-1  D-S1: dangling requires_detection_by 0 (transform 전부 detection 보유).
  P9-2  D-S4(wired): 배선 c.can_route_to_q → conditional edge 누락 0.
  P9-3  exercised Q 고립 0 (incoming conditional ≥1).
  P9-4  SSOT recover 무결성: q.recover_to_c_id 전부 c_units 존재.
  P9-5  SSOT strand 무결성: strand c_seq c_id·q_code 전부 존재 + terminal/q_code coupling.
  P9-6  vocab/anchors(G1): can_route_to_q ⊆ q_codes ⊆ anchors.q_codes.
  P9-7  scope_out 0 (deferred.scope_out_edges 빈 + stats 0) — GAP-28 Decision C.
  P9-8  unreached Q documented + router 전부 미배선(정직한 경계, D-S4 위반 아님).
  P9-9  anchors root 위치 로드(GAP-23 경로 drift를 현실로 고정).
  P9-10 banner 수치 build-time 독립 재계산 == index.html 임베디드(렌더 정직성).
  P9-11 C1(DoD#3): 모든 c(122) ≥1 strand 등장(dead c 0).
  P9-12 recover 렌더 정직성: 미배선 recover 타깃은 알려진 omit 집합(잘못된 라우팅 주장 0).

본 모듈은 `python3 tests/test_phase9_adversarial.py`로 직접 실행 시 수치 매트릭스를 출력한다
(review doc 증거 appendix용). pytest 하에서는 각 불변식을 단언한다.
"""
import json
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

TREE = json.loads((PROJECT_ROOT / "spec" / "decision_tree.json").read_text(encoding="utf-8"))
ANCHORS = json.loads((PROJECT_ROOT / "anchors.json").read_text(encoding="utf-8"))
CUNITS = {c["c_id"]: c for c in
          json.loads((PROJECT_ROOT / "spec" / "c_units.json").read_text(encoding="utf-8"))}
QCODES = {q["q_id"]: q for q in
          json.loads((PROJECT_ROOT / "spec" / "q_codes.json").read_text(encoding="utf-8"))}
STRANDS = json.loads((PROJECT_ROOT / "spec" / "strands.json").read_text(encoding="utf-8"))

from src.orchestrator import REGISTRY  # noqa: E402  — wired 57 (배선 SSOT)

REG = set(REGISTRY)
COST = {cid: c["cost"] for cid, c in CUNITS.items()}
QSET = set(QCODES)
ANCHOR_QS = set(ANCHORS["q_codes"])
COND = [(e["from"], e["to"]) for e in TREE["conditional_routing"]]
CONDSET = set(COND)
COND_TARGETS = {to for _, to in COND}
QPART = TREE["stats"]["q_partition"]
DEFERRED = TREE["deferred"]
STRAND_CS = {c for s in STRANDS for c in s["c_sequence"]}
INDEX_HTML = PROJECT_ROOT / "render" / "index.html"

# closure_proof.md INV-3 / strands_stats.md §6: 문서화된 C_dead(C_used 119 / C_all 122).
# 셋 다 미배선 fail-branch ROUTE c — best-strand(pass-only)는 미통과, 배선 시 D-S4 conditional edge로 편입.
DOCUMENTED_CDEAD = ["c0042", "c0043", "c0333"]


# ───────────────────── 불변식 계산 helper (단언과 매트릭스가 공유) ─────────────────────

def dangling_detection():
    """transform 중 requires_detection_by 누락, 또는 존재하지 않는 c 지목."""
    null_tf = [cid for cid, c in CUNITS.items()
               if c["kind"] == "transform" and not c.get("requires_detection_by")]
    dangling = [(cid, c["requires_detection_by"]) for cid, c in CUNITS.items()
                if c.get("requires_detection_by") and c["requires_detection_by"] not in CUNITS]
    return null_tf, dangling


def missing_ds4():
    """배선 c × can_route_to_q 중 conditional edge 부재 쌍."""
    return [(cid, q) for cid in REG
            for q in (CUNITS[cid].get("can_route_to_q") or [])
            if (cid, q) not in CONDSET]


def isolated_exercised_q():
    return [q for q in QPART["exercised"] if q not in COND_TARGETS]


def bad_recover():
    return [(qid, q.get("recover_to_c_id")) for qid, q in QCODES.items()
            if q.get("recover_to_c_id") not in CUNITS]


def bad_strand_refs():
    bad_c = sorted(STRAND_CS - set(CUNITS))
    bad_q = sorted({s["q_code"] for s in STRANDS
                    if s.get("q_code") is not None and s["q_code"] not in QSET})
    coupling = sum(1 for s in STRANDS
                   if (s["terminal"] == "QUARANTINE") != (s.get("q_code") is not None))
    return bad_c, bad_q, coupling


def vocab_anchor_violations():
    used_q = {q for c in CUNITS.values() for q in (c.get("can_route_to_q") or [])}
    not_in_qset = sorted(used_q - QSET)
    qset_not_anchor = sorted(QSET - ANCHOR_QS)
    return not_in_qset, qset_not_anchor


def scope_out_state():
    return (DEFERRED["scope_out_edges"],
            TREE["stats"]["scope_out_edges"],
            TREE["stats"]["scope_out_strands"])


def unreached_audit():
    """unreached Q 각: deferred 문서화 + 배선 router 0 + conditional target 부재."""
    documented = {d["q"] for d in DEFERRED["unreached_q"]}
    rows = []
    for q in QPART["unreached"]:
        wired_routers = [cid for cid in REG if q in (CUNITS[cid].get("can_route_to_q") or [])]
        rows.append({
            "q": q,
            "documented": q in documented,
            "wired_routers": wired_routers,
            "in_cond_targets": q in COND_TARGETS,
        })
    return rows


def anchors_location():
    return (PROJECT_ROOT / "anchors.json").is_file(), (PROJECT_ROOT / "spec" / "anchors.json").is_file()


def banner_recompute():
    """build_html.boundary_stats를 독립 재현해 index.html 임베디드 DT_BANNER와 비교."""
    from collections import Counter
    term = Counter(s["terminal"] for s in STRANDS)
    computed = {
        "total_strands": len(STRANDS),
        "wired_c": len(REG),
        "auto": term.get("AUTO", 0),
        "repair": term.get("REPAIR", 0),
        "complete": term.get("AUTO", 0) + term.get("REPAIR", 0),
        "quarantine": term.get("QUARANTINE", 0),
        "invalid": term.get("INVALID", 0),
        "unsupported": term.get("UNSUPPORTED", 0),
        "realized_pure": TREE["stats"]["pure_realized_strands"],
        "unwired_c": len(STRAND_CS - REG),
        "static_q": len(QPART["static_no_strand"]),
        "deferred_total": len(DEFERRED["unreached_q"]) + len(DEFERRED["spec_decisions"]),
    }
    html = INDEX_HTML.read_text(encoding="utf-8")
    m = re.search(r"var DT_BANNER=(\{[^}]*\})", html)
    embedded = json.loads(m.group(1)) if m else None
    return computed, embedded


def c1_dead_c():
    """DoD#3 C1: 모든 c가 ≥1 strand 등장. 미등장 = dead c 후보."""
    return sorted(set(CUNITS) - STRAND_CS)


def recover_omitted_targets():
    """recover_to_c_id 중 미배선 타깃(렌더가 정직히 omit해야 하는 집합)."""
    return sorted({q["recover_to_c_id"] for q in QCODES.values()
                   if q.get("recover_to_c_id") not in REG and q.get("recover_to_c_id") in CUNITS})


# ───────────────────────────────── pytest 단언 ─────────────────────────────────

def test_p9_1_no_dangling_detection():
    """P9-1 D-S1: transform 전부 requires_detection_by 보유 + dangling 0."""
    null_tf, dangling = dangling_detection()
    assert null_tf == [], f"transform without detection: {null_tf}"
    assert dangling == [], f"dangling requires_detection_by: {dangling}"


def test_p9_2_ds4_wired_no_missing_edge():
    """P9-2 D-S4(wired): 배선 c.can_route_to_q → conditional edge 누락 0."""
    assert missing_ds4() == [], f"missing conditional edges: {missing_ds4()}"


def test_p9_3_no_isolated_exercised_q():
    """P9-3: exercised Q(13) 전부 incoming conditional edge ≥1."""
    assert isolated_exercised_q() == [], f"isolated exercised Q: {isolated_exercised_q()}"


def test_p9_4_recover_targets_exist():
    """P9-4 SSOT: 모든 q.recover_to_c_id 가 c_units 에 존재."""
    assert bad_recover() == [], f"dangling recover_to_c_id: {bad_recover()}"


def test_p9_5_strand_refs_valid():
    """P9-5 SSOT: strand c_seq·q_code 전부 존재 + QUARANTINE⟺q_code coupling."""
    bad_c, bad_q, coupling = bad_strand_refs()
    assert bad_c == [], f"strand references unknown c: {bad_c}"
    assert bad_q == [], f"strand references unknown q: {bad_q}"
    assert coupling == 0, f"terminal/q_code coupling violations: {coupling}"


def test_p9_6_vocab_anchor_subset():
    """P9-6 G1: can_route_to_q ⊆ q_codes ⊆ anchors.q_codes (hallucination 차단)."""
    not_in_qset, qset_not_anchor = vocab_anchor_violations()
    assert not_in_qset == [], f"can_route_to_q not in q_codes: {not_in_qset}"
    assert qset_not_anchor == [], f"q_codes not in anchors: {qset_not_anchor}"


def test_p9_7_scope_out_zero():
    """P9-7: scope_out 0 (GAP-28 Decision C RESOLVE)."""
    edges, stat_edges, stat_strands = scope_out_state()
    assert edges == [], f"deferred.scope_out_edges not empty: {edges}"
    assert stat_edges == 0 and stat_strands == 0, (stat_edges, stat_strands)


def test_p9_8_unreached_q_documented_and_unwired():
    """P9-8: unreached Q(4) 전부 deferred 문서화 + 배선 router 0 + conditional target 부재.
    → 고립이 아니라 '미배선 source의 정직한 경계'(D-S4 위반 아님)."""
    for row in unreached_audit():
        assert row["documented"], f"{row['q']} not documented in deferred.unreached_q"
        assert row["wired_routers"] == [], f"{row['q']} has wired router(s): {row['wired_routers']}"
        assert not row["in_cond_targets"], f"{row['q']} unexpectedly has conditional incoming"


def test_p9_9_anchors_at_root_not_spec():
    """P9-9: anchors.json 은 repo ROOT 에 존재(코드가 거기서 로드), spec/ 엔 없음.
    → 'MISSING'이 아니라 CLAUDE.md 레이아웃 경로 drift(기존 GAP-23 OPEN)의 현실 고정."""
    root_exists, spec_exists = anchors_location()
    assert root_exists, "anchors.json must exist at PROJECT_ROOT"
    assert not spec_exists, "spec/anchors.json absence is the GAP-23 path-drift reality"


def test_p9_10_banner_numbers_build_time_verifiable():
    """P9-10 렌더 정직성: index.html DT_BANNER == 독립 재계산(strands.json+decision_tree.json).
    배너 수치는 하드코딩이 아니라 spec 파생(검증가능)."""
    computed, embedded = banner_recompute()
    assert embedded is not None, "DT_BANNER not found in index.html"
    assert computed == embedded, f"banner drift:\n  computed={computed}\n  embedded={embedded}"


def test_p9_11_c1_dead_c_matches_documented():
    """P9-11 DoD#3 C1: strand 미등장 dead c == 문서화된 C_dead {c0042,c0043,c0333}(UNDOCUMENTED dead 0).
    셋 다 미배선 fail-branch ROUTE c. closure_proof.md INV-3·strands_stats.md §6 기록.
    ★ closure_proof Option C는 "배선 시 tree-live" forward-looking(2026-06-03 시제 정정·GAP-36 RESOLVED);
    현 57-wired scope에선 미배선 → tree 부재(C1 OR절 미충족, ②latent). 본 test는 '미기록 dead c가 새로 생기지 않음'을 회귀방지(정직한 경계 고정)."""
    assert c1_dead_c() == DOCUMENTED_CDEAD, f"dead c set drifted from documented C_dead: {c1_dead_c()}"


def test_p9_12_recover_unwired_targets_known():
    """P9-12 렌더 정직성: 미배선 recover 타깃은 알려진 omit 집합(잘못된 라우팅 주장 0).
    렌더는 wired+reachable recover edge만 그린다(test_render.py 교차)."""
    assert recover_omitted_targets() == ["c0330", "c0368", "c0499"], recover_omitted_targets()


# ─────────────────────────── 직접 실행: 수치 매트릭스 출력 ───────────────────────────

def _matrix():
    def line(tag, ok, detail):
        print(f"  [{'PASS' if ok else 'FAIL'}] {tag:7} {detail}")

    print("=" * 78)
    print("PHASE 9 — 적대적 교차-SSOT 검증 매트릭스 (read-only, falsifiable)")
    print("=" * 78)
    print(f"  로드: c_units {len(CUNITS)} · q_codes {len(QSET)} · wired REGISTRY {len(REG)} · "
          f"strands {len(STRANDS)} · tree nodes {len(TREE['nodes'])} · cond {len(COND)}")
    print("-" * 78)

    null_tf, dangling = dangling_detection()
    line("P9-1", not null_tf and not dangling,
         f"D-S1 dangling detection: null_tf={len(null_tf)} dangling={len(dangling)}")
    line("P9-2", not missing_ds4(), f"D-S4 wired 누락 edge: {len(missing_ds4())}")
    line("P9-3", not isolated_exercised_q(), f"exercised Q 고립: {len(isolated_exercised_q())}")
    line("P9-4", not bad_recover(), f"dangling recover_to_c_id: {len(bad_recover())}")
    bad_c, bad_q, coupling = bad_strand_refs()
    line("P9-5", not bad_c and not bad_q and coupling == 0,
         f"strand bad_c={len(bad_c)} bad_q={len(bad_q)} coupling_viol={coupling}")
    niq, qna = vocab_anchor_violations()
    line("P9-6", not niq and not qna, f"can_route∉q_codes={len(niq)} q_codes∉anchors={len(qna)}")
    e, se, ss = scope_out_state()
    line("P9-7", not e and se == 0 and ss == 0, f"scope_out edges={len(e)} stat_edges={se} stat_strands={ss}")
    ua = unreached_audit()
    ok8 = all(r["documented"] and not r["wired_routers"] and not r["in_cond_targets"] for r in ua)
    line("P9-8", ok8, "unreached Q=" + ",".join(
        f"{r['q']}(doc={r['documented']},wired_router={len(r['wired_routers'])})" for r in ua))
    re_, se_ = anchors_location()
    line("P9-9", re_ and not se_, f"anchors root={re_} spec/anchors={se_} (GAP-23 drift)")
    computed, embedded = banner_recompute()
    line("P9-10", computed == embedded, f"banner build-time 재계산 == 임베디드: {computed == embedded}")
    line("P9-11", c1_dead_c() == DOCUMENTED_CDEAD,
         f"C1 dead c == 문서화 C_dead {DOCUMENTED_CDEAD}: 실측 {c1_dead_c()} (미기록 dead 0)")
    line("P9-12", recover_omitted_targets() == ["c0330", "c0368", "c0499"],
         f"미배선 recover omit 집합: {recover_omitted_targets()}")
    print("-" * 78)

    # 2축 보조 통계(은폐 0 입증용 — review doc §E)
    from collections import Counter
    term = Counter(s["terminal"] for s in STRANDS)
    qcnt = Counter(s["q_code"] for s in STRANDS if s.get("q_code"))
    unreal6 = sum(qcnt[q] for q in (QPART["static_no_strand"] + QPART["unreached"]))
    print("  [축1 oracle] terminal:", dict(term), "| complete(AUTO+REPAIR)=",
          term["AUTO"] + term["REPAIR"])
    print(f"  [축2 wired ] banner.realized_pure={embedded['realized_pure']} · "
          f"unwired_c={embedded['unwired_c']} · static_q={embedded['static_q']} · "
          f"deferred={embedded['deferred_total']}")
    print(f"  [경계 정직] oracle이 미실현/미도달 Q(Q05/Q10/Q15A/B/C/X)로 보낸 strand={unreal6} "
          f"→ QUARANTINE(사람개입)으로 정직 집계, 그 Q-terminal은 wired 미실현 표시(은폐 0)")
    print("=" * 78)


if __name__ == "__main__":
    _matrix()
