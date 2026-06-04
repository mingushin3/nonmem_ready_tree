"""render/index_v2.html(쉬운 설명 뷰 + 진단 마법사) 검증 — 엔진/SSOT 무수정(신규 파일).

★ 핵심: 마법사 판정이 src.adapter.ingest() 정본과 동일함을 증명한다.
  (1) WIZARD 상수 == live 어댑터 상수(drift 불가)
  (2) wizard_verdict_from_structure == ingest 의 c_sequence/honest-stop (대표 합성 fixture 5종)
  (3) JS wizardVerdict == python wizard_verdict_from_answers (node로 실행 비교 — 모든 답 조합)
  (4) honest-stop recipe WU 매핑 == recipe_emitter
  (5) 빌드 결정성 + 용어집 완전성

합성 xlsx는 openpyxl로 tmp_path에 생성(D-G3: 합성만). conftest가 PROJECT_ROOT를 sys.path에 추가.
"""
import json
import shutil
import subprocess
import sys
from pathlib import Path

import openpyxl
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "render"))

import build_html_v2 as V  # noqa: E402  (import 시 데이터층 빌드 — index_v2.html 미작성)

from src.adapter import ingest  # noqa: E402
from src.adapter.xlsx_ingester import read_workbook_structure  # noqa: E402
from src.adapter import xlsx_ingester as XI  # noqa: E402
from src.adapter.navigator import _FILE_PROPERTY, _DATA_DEPENDENT, _CANON_ORDER  # noqa: E402


# ----- 합성 fixture 빌더(test_adapter_tier0._save idiom) ---------------------

def _save(path, sheets):
    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    for title, rows in sheets:
        ws = wb.create_sheet(title=title)
        for r in rows:
            ws.append(r)
    wb.save(path)
    return str(path)


def make_tidy(tmp):
    return _save(tmp / "tidy.xlsx", [("data", [
        ["Subject", "Time", "Conc"], [1, 0, 0.0], [1, 1, 5.2], [2, 0, 0.0], [2, 1, 6.4]])])


def make_qa(tmp):
    return _save(tmp / "qa.xlsx", [("Result", [
        ["Sample", "Time", "Conc"], ["Standard 1", 0, 0.1], ["S01", 1, 5.2], ["S02", 2, 3.1]])])


def make_param(tmp):
    return _save(tmp / "param.xlsx", [("Data", [
        ["Parameter", "Unit", "Mean"], ["Cmax", "ng/mL", 12.3], ["AUC", "ng*h/mL", 55.1]])])


def make_wide(tmp):
    return _save(tmp / "wide.xlsx", [("Result", [
        ["Time", "Animal1", "Animal2", "Animal3"], [0, 0.0, 0.0, 0.0], [1, 5.1, 6.2, 4.9]])])


def make_unknown(tmp):
    return _save(tmp / "unk.xlsx", [("misc", [["Foo", "Bar"], ["a", "b"], ["c", "d"]])])


REPRESENTATIVE = [
    ("tidy", make_tidy, True),
    ("qa", make_qa, False),
    ("param", make_param, False),
    ("wide", make_wide, False),
    ("unknown", make_unknown, False),
]

FULL_BAND = ["c0201", "c0203", "c0205", "c0210", "c0211", "c0212",
             "c0214", "c0215", "c0216", "c0305", "c0310", "c0312", "c0314"]


# ===== (1) 상수 동일성 — drift 불가 =========================================

def test_wizard_constants_match_adapter():
    assert V.WIZARD["file_property_c"] == list(_FILE_PROPERTY)
    assert V.WIZARD["data_dependent_c"] == list(_DATA_DEPENDENT)
    assert V.WIZARD["canon_order"] == list(_CANON_ORDER)
    assert V.WIZARD["qa_tokens"] == list(XI._QA_TOKENS)


# ===== (2) 마법사 판정 == ingest ===========================================

@pytest.mark.parametrize("name,builder,exp_faithful", REPRESENTATIVE)
def test_wizard_verdict_equals_ingest(tmp_path, name, builder, exp_faithful):
    path = builder(tmp_path)
    truth = ingest(path)
    struct = read_workbook_structure(path)
    v = V.wizard_verdict_from_structure(struct)

    assert v["faithful_tidy"] == exp_faithful, name
    assert v["c_sequence"] == truth["dispatched"]["c_sequence"], name
    assert v["entry_node"] == truth["entry_node"] == "N0"
    if not exp_faithful:
        assert truth["stop"]["at"] == "structure-recognition"
        assert truth["stop"]["gap"] == "GAP-37"
        assert v["stop_at"] == "structure-recognition"
        assert v["gap"] == "GAP-37"
        assert v["c_sequence"] == ["c0201", "c0210"]


def test_tidy_dispatches_full_band(tmp_path):
    v = V.wizard_verdict_from_structure(read_workbook_structure(make_tidy(tmp_path)))
    assert v["c_sequence"] == FULL_BAND


def test_tidy_without_subject_drops_c0212(tmp_path):
    """subject 열이 없으면 c0212 precondition 미충족(navigator._precondition_ok 미러)."""
    path = _save(tmp_path / "nosub.xlsx", [("data", [
        ["Time", "Conc"], [0, 0.0], [1, 5.2], [2, 6.4]])])
    truth = ingest(path)
    v = V.wizard_verdict_from_structure(read_workbook_structure(path))
    assert v["c_sequence"] == truth["dispatched"]["c_sequence"]
    assert "c0212" not in v["c_sequence"]


# ===== (3) JS wizardVerdict == python wizard_verdict_from_answers ===========

def _extract_js_fn(html, fnname):
    i = html.index("function " + fnname + "(")
    depth, k, started = 0, i, False
    while k < len(html):
        ch = html[k]
        if ch == "{":
            depth += 1
            started = True
        elif ch == "}":
            depth -= 1
            if started and depth == 0:
                return html[i:k + 1]
        k += 1
    raise AssertionError("function %s not found" % fnname)


def test_js_wizard_matches_python(tmp_path):
    node = shutil.which("node")
    if node is None:
        pytest.skip("node 미설치 — JS↔python 동치 검사 생략")
    html = V.build_html()
    fn = _extract_js_fn(html, "wizardVerdict")
    cunits = {k: {"can_route_to_q": c.get("can_route_to_q", [])} for k, c in V.B.CUNITS.items()}
    harness = (
        "var WIZARD=" + json.dumps(V.WIZARD) + ";\n"
        "var CUNITS=" + json.dumps(cunits) + ";\n"
        + fn + "\n"
        "var out=[];\n"
        "[true,false].forEach(function(t){[true,false].forEach(function(s){\n"
        "  var a={tidy:t,has_subject:s};var v=wizardVerdict(a);\n"
        "  out.push({a:a,c:v.c_sequence,f:v.faithful,q:v.qcodes.slice().sort()});\n"
        "});});\n"
        "console.log(JSON.stringify(out));\n"
    )
    p = tmp_path / "harness.js"
    p.write_text(harness, encoding="utf-8")
    r = subprocess.run([node, str(p)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    for item in json.loads(r.stdout):
        a = item["a"]
        pv = V.wizard_verdict_from_answers(a)
        assert item["c"] == pv["c_sequence"], (a, item["c"], pv["c_sequence"])
        assert item["f"] == pv["faithful_tidy"], a
        pq = set()
        for cid in pv["c_sequence"]:
            pq |= set(V.B.CUNITS.get(cid, {}).get("can_route_to_q", []))
        assert set(item["q"]) == pq, (a, sorted(item["q"]), sorted(pq))


# ===== (4) honest-stop recipe WU 매핑 == recipe_emitter ====================

@pytest.mark.parametrize("wkey,builder,wu_name", [
    ("qa", make_qa, "QA-strip"),
    ("param", make_param, "param-summary-reserve"),
    ("subject_wide", make_wide, "pivot-wide-to-long"),
])
def test_wu_mapping_matches_recipe(tmp_path, wkey, builder, wu_name):
    truth = ingest(builder(tmp_path))
    names = {w["name"] for w in truth["recipe"]["work_units"]}
    assert wu_name in names, (wkey, names)
    assert V.WIZARD_WU[wkey] == wu_name


# ===== (5) 결정성 + 용어집 완전성 + 색 =====================================

def test_v2_build_deterministic():
    assert V.build_html() == V.build_html()


def test_glossary_complete():
    assert V.assert_glossary_complete() is True


def test_glossary_covers_every_state():
    for ax, states in V.B.AXIS_STATES.items():
        for s in states:
            assert V.GLOSSARY["state"].get(ax + "::" + s), (ax, s)


def test_glossary_covers_every_qcode_and_axis():
    for q in V.B.Q_IDS:
        assert V.GLOSSARY["qcode"].get(q), q
    for ax in V.B.AXIS_IDS:
        assert V.GLOSSARY["axis"].get(ax), ax


def test_v2_recolor_no_legacy_highlight_colors():
    html = V.build_html()
    for stale in ("#FFD700", "#FFF8B0", "#c9920e"):
        assert stale not in html, stale
    assert V.AMBER in html and V.TEAL in html


def test_v2_does_not_touch_index_html():
    """v2 빌드는 정본 index.html을 만들지 않는다(별도 산출물만)."""
    html = V.build_html()
    assert "index v2" in html
    assert "내 파일 진단" in html
