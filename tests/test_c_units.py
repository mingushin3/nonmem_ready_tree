"""TDD tests for c-unit implementations (Phase 4)."""

import pandas as pd
import numpy as np
import pytest

from src.c_units.c0001_verify_column_schema import verify_column_schema
from src.c_units.c0010_assign_evid import assign_evid
from src.c_units.c0011_assign_mdv import assign_mdv
from src.c_units.c0012_assign_amt import assign_amt
from src.c_units.c0014_assign_rate import assign_rate
from src.c_units.c0013_assign_cmt import assign_cmt
from src.c_units.c0015_assign_addl import assign_addl
from src.c_units.c0016_assign_ii import assign_ii
from src.c_units.c0208_classify_analyte_column import classify_analyte_column
from src.c_units.c0017_assign_dv import assign_dv
from src.c_units.c0018_assign_id import assign_id
from src.c_units.c0019_assign_time import assign_time
from src.c_units.c0020_assign_blq_flag import assign_blq_flag
from src.c_units.c0021_assign_lloq import assign_lloq
from src.c_units.c0022_assign_baseline_covariate import assign_baseline_covariate
from src.c_units.c0023_assign_time_varying_covariate import assign_time_varying_covariate
from src.c_units.c0140_assign_baseline_covariate import assign_baseline_covariate as assign_baseline_covariate_l3
from src.c_units.c0141_assign_time_varying_covariate import assign_time_varying_covariate as assign_time_varying_covariate_l3
from src.c_units.c0121_pivot_covariate_layout import pivot_covariate_layout
from src.c_units.c0200_verify_a0_analysis_intent import verify_a0_analysis_intent
from src.c_units.c0204_verify_amt import verify_amt
from src.c_units.c0201_detect_sheet_inventory import detect_sheet_inventory
from src.c_units.c0202_classify_regimen_descriptor import classify_regimen_descriptor
from src.c_units.c0203_detect_time_format import detect_time_format
from src.c_units.c0205_detect_blq_token import detect_blq_token
from src.c_units.c0206_classify_row_ordering import classify_row_ordering
from src.c_units.c0207_classify_covariate_layout import classify_covariate_layout
from src.c_units.c0209_verify_cross_column_invariant import verify_cross_column_invariant
from src.c_units.c0210_detect_source_format import detect_source_format
from src.c_units.c0340_detect_merged_cell import detect_merged_cell
from src.c_units.c0341_propagate_merged_cell import propagate_merged_cell
from src.c_units.c0213_verify_time_anchor import verify_time_anchor
from src.c_units.c0251_route_time_format import route_time_format
from src.c_units.c0310_detect_time_format import detect_time_format_mess
from src.c_units.c0314_detect_time_anchor import detect_time_anchor
from src.c_units.c0311_convert_time_format import convert_time_format
from src.c_units.c0315_convert_time_anchor import convert_time_anchor
from src.c_units.c0312_detect_timezone import detect_timezone
from src.c_units.c0313_normalize_timezone import normalize_timezone


class TestC0340:
    """c0340 — 병합 셀 감지 (DETECT MERGED_CELL)

    postcondition_predicate:
        isinstance(meta.get('has_merged_cells'), bool)

    srp_intent: DETECT MERGED_CELL
    kind: detect
    requires_detection_by: null
    can_route_to_q: []
    verify_visualization:
        pass_route_to: c0341
        fail_route_to: null
    """

    def test_happy(self, load_fixture_with_meta):
        """값-다음-NaN 병합 잔존 존재(dose 컬럼) → has_merged_cells=True, pass→c0341."""
        df, meta, expected = load_fixture_with_meta("c0340", "happy")
        result = detect_merged_cell(df, meta)
        assert result["has_merged_cells"] == expected["has_merged_cells"]
        assert result["pass"] == expected["pass"]
        assert result["route_to_q"] == expected["route_to_q"]
        assert isinstance(meta.get('has_merged_cells'), bool)

    def test_edge(self, load_fixture_with_meta):
        """선행 NaN + 전체-NaN 컬럼(잔존 아님) → has_merged_cells=False."""
        df, meta, expected = load_fixture_with_meta("c0340", "edge")
        result = detect_merged_cell(df, meta)
        assert result["has_merged_cells"] == expected["has_merged_cells"]
        assert result["pass"] == expected["pass"]
        assert isinstance(meta.get('has_merged_cells'), bool)

    def test_trap(self, load_fixture_with_meta):
        """NaN 있으나 값-다음-NaN 없음(선행 NaN 블록) → False (naive any-NaN 감지기 silent-pass 차단)."""
        df, meta, expected = load_fixture_with_meta("c0340", "trap")
        result = detect_merged_cell(df, meta)
        assert result["has_merged_cells"] == expected["has_merged_cells"]
        assert result["has_merged_cells"] is False
        assert isinstance(meta.get('has_merged_cells'), bool)


class TestC0341:
    """c0341 — 병합 셀 전파 (PROPAGATE MERGED_CELL)

    postcondition_predicate:
        not meta.get('has_merged_cells', False) or not any((df[c].isna() & df[c].shift().notna()).any() for c in df.columns)

    srp_intent: PROPAGATE MERGED_CELL
    kind: transform
    requires_detection_by: c0340
    can_route_to_q: []
    """

    @staticmethod
    def _nan_safe(series):
        """list()로 비교 시 NaN!=NaN 문제 회피: NaN→None 매핑."""
        return [None if pd.isna(x) else x for x in series]

    def test_happy(self, load_fixture_with_meta):
        """병합 잔존 forward-fill → dose 전파 완료([100,100,100,200,200]), 잔존 0."""
        df, meta, expected = load_fixture_with_meta("c0341", "happy")
        result = propagate_merged_cell(df, meta)
        assert result["success"] == expected["success"]
        df_out = result["df"]
        assert not meta.get('has_merged_cells', False) or not any((df_out[c].isna() & df_out[c].shift().notna()).any() for c in df_out.columns)
        assert list(df_out["dose"]) == expected["dose"]
        assert list(df_out["subject_id"]) == expected["subject_id"]

    def test_edge(self, load_fixture_with_meta):
        """선행 NaN은 anchor 없음 → 보존([NaN,5,5]); clean 컬럼 불변(역방향 backfill 금지)."""
        df, meta, expected = load_fixture_with_meta("c0341", "edge")
        result = propagate_merged_cell(df, meta)
        assert result["success"] == expected["success"]
        df_out = result["df"]
        assert not meta.get('has_merged_cells', False) or not any((df_out[c].isna() & df_out[c].shift().notna()).any() for c in df_out.columns)
        assert self._nan_safe(df_out["lead"]) == expected["lead"]
        assert list(df_out["clean"]) == expected["clean"]

    def test_trap(self, load_fixture_with_meta):
        """교차컬럼/구조 bleed 차단: 컬럼별 수직 ffill만(axis=1 가로채우기·역방향 금지)."""
        df, meta, expected = load_fixture_with_meta("c0341", "trap")
        result = propagate_merged_cell(df, meta)
        assert result["success"] == expected["success"]
        df_out = result["df"]
        assert not meta.get('has_merged_cells', False) or not any((df_out[c].isna() & df_out[c].shift().notna()).any() for c in df_out.columns)
        assert list(df_out["A"]) == expected["A"]
        assert self._nan_safe(df_out["B"]) == expected["B"]


class TestC0001:
    """c0001 — L-2 컬럼 스키마 검증 (VERIFY COLUMN_SCHEMA)

    postcondition_predicate:
        all(col in df.columns for col in ['subject_id', 'event_type', 'time_value', 'dv_value'])
        and df[['subject_id', 'event_type', 'time_value']].notna().all().all()

    srp_intent: VERIFY COLUMN_SCHEMA
    kind: verify
    verify_visualization:
        pass_route_to: c0010
        fail_route_to: INVALID
    """

    def test_happy(self, load_fixture):
        """모든 필수 컬럼 존재, 핵심 컬럼 결측 없음 → pass, route to c0010."""
        df, expected = load_fixture("c0001", "happy")
        result = verify_column_schema(df)
        assert result["pass"] == expected["pass"]
        assert result["route_to"] == expected["route_to"]
        assert result["missing_columns"] == expected["missing_columns"]

    def test_edge(self, load_fixture):
        """최소 1행, 경계값 → pass, route to c0010."""
        df, expected = load_fixture("c0001", "edge")
        result = verify_column_schema(df)
        assert result["pass"] == expected["pass"]
        assert result["route_to"] == expected["route_to"]

    def test_trap(self, load_fixture):
        """event_type 컬럼 누락 → fail, route to INVALID."""
        df, expected = load_fixture("c0001", "trap")
        result = verify_column_schema(df)
        assert result["pass"] == expected["pass"]
        assert result["route_to"] == expected["route_to"]
        assert "event_type" in result["missing_columns"]

    def test_trap2(self, load_fixture):
        """event_type 전체 NaN — postcond ② notna 위반 → fail, route to INVALID."""
        df, expected = load_fixture("c0001", "trap2")
        result = verify_column_schema(df)
        assert result["pass"] == expected["pass"]
        assert result["route_to"] == expected["route_to"]


class TestC0010:
    """c0010 — EVID 부여 (ASSIGN EVID)

    postcondition_predicate:
        'EVID' in df.columns and df['EVID'].isin([0,1,2,3,4]).all() and df['EVID'].notna().all()

    srp_intent: ASSIGN EVID
    kind: transform
    requires_detection_by: c0001
    can_route_to_q: [Q04]
    """

    def test_happy(self, load_fixture):
        """5종 event_type 모두 정상 매핑 → success, EVID 값 일치."""
        df_in, expected = load_fixture("c0010", "happy")
        result = assign_evid(df_in)
        assert result["success"] == expected["success"]
        df_out = result["df"]
        assert 'EVID' in df_out.columns and df_out['EVID'].isin([0,1,2,3,4]).all() and df_out['EVID'].notna().all()
        assert list(df_out["EVID"]) == expected["EVID"]

    def test_edge(self, load_fixture):
        """단일 행(obs) → success, EVID=[0]."""
        df_in, expected = load_fixture("c0010", "edge")
        result = assign_evid(df_in)
        assert result["success"] == expected["success"]
        df_out = result["df"]
        assert 'EVID' in df_out.columns and df_out['EVID'].isin([0,1,2,3,4]).all() and df_out['EVID'].notna().all()
        assert list(df_out["EVID"]) == expected["EVID"]

    def test_trap_col(self, load_fixture):
        """event_type 컬럼 부재(EventType) — postcond clause 1 위반 → Q04."""
        df_in, expected = load_fixture("c0010", "trap_col")
        result = assign_evid(df_in)
        assert result["success"] == expected["success"]
        assert result["route_to_q"] == expected["route_to_q"]

    def test_trap_range(self, load_fixture):
        """event_type에 매핑 불가 값('other') — postcond clause 2 위반 → Q04."""
        df_in, expected = load_fixture("c0010", "trap_range")
        result = assign_evid(df_in)
        assert result["success"] == expected["success"]
        assert result["route_to_q"] == expected["route_to_q"]

    def test_trap_na(self, load_fixture):
        """event_type에 NaN 포함 — postcond clause 3 위반 → Q04."""
        df_in, expected = load_fixture("c0010", "trap_na")
        result = assign_evid(df_in)
        assert result["success"] == expected["success"]
        assert result["route_to_q"] == expected["route_to_q"]


class TestC0011:
    """c0011 — MDV 부여 (ASSIGN MDV)

    postcondition_predicate:
        'MDV' in df.columns and df['MDV'].isin([0,1]).all()
        and (df.loc[df['EVID'].isin([1,2,3,4]), 'MDV'] == 1).all()

    srp_intent: ASSIGN MDV
    kind: transform
    requires_detection_by: c0010
    can_route_to_q: []
    """

    def test_happy(self, load_fixture):
        """dose/obs/missing-obs 혼합 → success, MDV 값 일치."""
        df_in, expected = load_fixture("c0011", "happy")
        result = assign_mdv(df_in)
        assert result["success"] == expected["success"]
        df_out = result["df"]
        assert 'MDV' in df_out.columns and df_out['MDV'].isin([0,1]).all() and (df_out.loc[df_out['EVID'].isin([1,2,3,4]), 'MDV'] == 1).all()
        assert list(df_out["MDV"]) == expected["MDV"]

    def test_edge(self, load_fixture):
        """전부 dose(EVID=1,3) → 모든 MDV=1."""
        df_in, expected = load_fixture("c0011", "edge")
        result = assign_mdv(df_in)
        assert result["success"] == expected["success"]
        df_out = result["df"]
        assert 'MDV' in df_out.columns and df_out['MDV'].isin([0,1]).all() and (df_out.loc[df_out['EVID'].isin([1,2,3,4]), 'MDV'] == 1).all()
        assert list(df_out["MDV"]) == expected["MDV"]

    def test_trap_col(self, load_fixture):
        """EVID 컬럼 부재('evid') — postcond clause 1 위반 → fail."""
        df_in, expected = load_fixture("c0011", "trap_col")
        result = assign_mdv(df_in)
        assert result["success"] == expected["success"]

    def test_trap_nan_evid(self, load_fixture):
        """EVID에 NaN 포함 — postcond clause 2 위반 위험 → fail."""
        df_in, expected = load_fixture("c0011", "trap_nan_evid")
        result = assign_mdv(df_in)
        assert result["success"] == expected["success"]

    def test_trap_dose_mdv0(self, load_fixture):
        """EVID=1인데 dv_value 있음 — naive impl이 MDV=0 → postcond clause 3 위반."""
        df_in, expected = load_fixture("c0011", "trap_dose_mdv0")
        result = assign_mdv(df_in)
        assert result["success"] == expected["success"]
        df_out = result["df"]
        assert (df_out.loc[df_out['EVID'].isin([1,2,3,4]), 'MDV'] == 1).all()
        assert list(df_out["MDV"]) == expected["MDV"]


class TestC0012:
    """c0012 — AMT 부여 (ASSIGN AMT)

    postcondition_predicate:
        'AMT' in df.columns and (df.loc[df['EVID'].isin([1,3,4]), 'AMT'] > 0).all()
        and (df.loc[df['EVID'].isin([0,2]), 'AMT'] == 0).all()

    srp_intent: ASSIGN AMT
    kind: transform
    requires_detection_by: c0010
    can_route_to_q: [Q08]
    """

    def test_happy(self, load_fixture):
        """dose/obs/reset 혼합 → success, AMT 값 일치."""
        df_in, expected = load_fixture("c0012", "happy")
        result = assign_amt(df_in)
        assert result["success"] == expected["success"]
        df_out = result["df"]
        assert 'AMT' in df_out.columns and (df_out.loc[df_out['EVID'].isin([1,3,4]), 'AMT'] > 0).all() and (df_out.loc[df_out['EVID'].isin([0,2]), 'AMT'] == 0).all()
        assert list(df_out["AMT"]) == expected["AMT"]

    def test_edge(self, load_fixture):
        """전부 obs(EVID=0) → 모든 AMT=0."""
        df_in, expected = load_fixture("c0012", "edge")
        result = assign_amt(df_in)
        assert result["success"] == expected["success"]
        df_out = result["df"]
        assert 'AMT' in df_out.columns and (df_out.loc[df_out['EVID'].isin([0,2]), 'AMT'] == 0).all()
        assert list(df_out["AMT"]) == expected["AMT"]

    def test_trap_col(self, load_fixture):
        """dose_amount 컬럼 부재 — postcond clause 1 위반 → Q08."""
        df_in, expected = load_fixture("c0012", "trap_col")
        result = assign_amt(df_in)
        assert result["success"] == expected["success"]
        assert result["route_to_q"] == expected["route_to_q"]

    def test_trap_dose_zero(self, load_fixture):
        """EVID=1인데 dose_amount=0 — postcond clause 2 위반 → Q08."""
        df_in, expected = load_fixture("c0012", "trap_dose_zero")
        result = assign_amt(df_in)
        assert result["success"] == expected["success"]
        assert result["route_to_q"] == expected["route_to_q"]

    def test_trap_obs_nonzero(self, load_fixture):
        """EVID=0인데 dose_amount=50 — naive impl이 AMT=50 → postcond clause 3 위반."""
        df_in, expected = load_fixture("c0012", "trap_obs_nonzero")
        result = assign_amt(df_in)
        assert result["success"] == expected["success"]
        df_out = result["df"]
        assert (df_out.loc[df_out['EVID'].isin([0,2]), 'AMT'] == 0).all()
        assert list(df_out["AMT"]) == expected["AMT"]


class TestC0014:
    """c0014 — RATE 부여 (ASSIGN RATE)

    postcondition_predicate:
        'RATE' in df.columns and df['RATE'].apply(lambda x: x == 0 or x > 0 or x == -1 or x == -2).all()
        and (df.loc[df['RATE'] > 0, 'AMT'] > 0).all() if 'AMT' in df.columns else True

    srp_intent: ASSIGN RATE
    kind: transform
    requires_detection_by: c0010
    can_route_to_q: []
    """

    def test_happy(self, load_fixture):
        """bolus/infusion/model_rate/model_duration 혼합 → success, RATE 값 일치."""
        df_in, expected = load_fixture("c0014", "happy")
        result = assign_rate(df_in)
        assert result["success"] == expected["success"]
        df_out = result["df"]
        assert 'RATE' in df_out.columns and df_out['RATE'].apply(lambda x: x == 0 or x > 0 or x == -1 or x == -2).all()
        if 'AMT' in df_out.columns:
            assert (df_out.loc[df_out['RATE'] > 0, 'AMT'] > 0).all()
        assert list(df_out["RATE"]) == expected["RATE"]

    def test_edge(self, load_fixture):
        """infusion 컬럼 없음(전부 bolus) → 모든 RATE=0."""
        df_in, expected = load_fixture("c0014", "edge")
        result = assign_rate(df_in)
        assert result["success"] == expected["success"]
        df_out = result["df"]
        assert 'RATE' in df_out.columns and (df_out['RATE'] == 0).all()
        assert list(df_out["RATE"]) == expected["RATE"]

    def test_trap_col(self, load_fixture):
        """EVID 컬럼 부재 — postcond clause 1 위반 → fail."""
        df_in, expected = load_fixture("c0014", "trap_col")
        result = assign_rate(df_in)
        assert result["success"] == expected["success"]

    def test_trap_invalid(self, load_fixture):
        """infusion_rate=-0.5(유효하지 않은 음수) — postcond clause 2 위반 방지, bolus 기본값."""
        df_in, expected = load_fixture("c0014", "trap_invalid")
        result = assign_rate(df_in)
        assert result["success"] == expected["success"]
        df_out = result["df"]
        assert df_out['RATE'].apply(lambda x: x == 0 or x > 0 or x == -1 or x == -2).all()
        assert list(df_out["RATE"]) == expected["RATE"]

    def test_trap_rate_amt(self, load_fixture):
        """RATE>0인데 AMT=0 — postcond clause 3 위반 → fail."""
        df_in, expected = load_fixture("c0014", "trap_rate_amt")
        result = assign_rate(df_in)
        assert result["success"] == expected["success"]


class TestC0208:
    """c0208 — A8 다약물/CMT 평가 (CLASSIFY ANALYTE_COLUMN)

    postcondition_predicate:
        meta.get('a8_state') in ['SINGLE-DRUG','MULTI-CMT-DEFINED','DDI-VICTIM-ONLY','DDI-VICTIM-PERPETRATOR','METABOLITE-DEFINED','CMT-POLICY-MISSING']

    srp_intent: CLASSIFY ANALYTE_COLUMN
    kind: detect
    can_route_to_q: [Q09]
    verify_visualization:
        pass_route_to: c0209
        fail_route_to: Q09
    """

    # --- 6 happy (one per a8_state) ---

    def test_happy_single_drug(self, load_fixture_with_meta):
        """단일 약물, 단일 경로 → SINGLE-DRUG."""
        df, meta, expected = load_fixture_with_meta("c0208", "happy_single_drug")
        result = classify_analyte_column(df, meta)
        assert result["a8_state"] == expected["a8_state"]
        assert result["pass"] == expected["pass"]
        assert result["route_to_q"] == expected["route_to_q"]
        assert meta.get('a8_state') in ['SINGLE-DRUG','MULTI-CMT-DEFINED','DDI-VICTIM-ONLY','DDI-VICTIM-PERPETRATOR','METABOLITE-DEFINED','CMT-POLICY-MISSING']

    def test_happy_multi_cmt(self, load_fixture_with_meta):
        """다경로(IV+PO) + cmt_map 정의됨 → MULTI-CMT-DEFINED."""
        df, meta, expected = load_fixture_with_meta("c0208", "happy_multi_cmt")
        result = classify_analyte_column(df, meta)
        assert result["a8_state"] == expected["a8_state"]
        assert result["pass"] == expected["pass"]
        assert result["route_to_q"] == expected["route_to_q"]
        assert meta.get('a8_state') in ['SINGLE-DRUG','MULTI-CMT-DEFINED','DDI-VICTIM-ONLY','DDI-VICTIM-PERPETRATOR','METABOLITE-DEFINED','CMT-POLICY-MISSING']

    def test_happy_ddi_victim_only(self, load_fixture_with_meta):
        """DDI study, victim만 → DDI-VICTIM-ONLY."""
        df, meta, expected = load_fixture_with_meta("c0208", "happy_ddi_victim")
        result = classify_analyte_column(df, meta)
        assert result["a8_state"] == expected["a8_state"]
        assert result["pass"] == expected["pass"]
        assert meta.get('a8_state') in ['SINGLE-DRUG','MULTI-CMT-DEFINED','DDI-VICTIM-ONLY','DDI-VICTIM-PERPETRATOR','METABOLITE-DEFINED','CMT-POLICY-MISSING']

    def test_happy_ddi_victim_perpetrator(self, load_fixture_with_meta):
        """DDI study, victim + perpetrator → DDI-VICTIM-PERPETRATOR."""
        df, meta, expected = load_fixture_with_meta("c0208", "happy_ddi_victim_perp")
        result = classify_analyte_column(df, meta)
        assert result["a8_state"] == expected["a8_state"]
        assert result["pass"] == expected["pass"]
        assert meta.get('a8_state') in ['SINGLE-DRUG','MULTI-CMT-DEFINED','DDI-VICTIM-ONLY','DDI-VICTIM-PERPETRATOR','METABOLITE-DEFINED','CMT-POLICY-MISSING']

    def test_happy_metabolite(self, load_fixture_with_meta):
        """Parent + metabolite 매핑 정의됨 → METABOLITE-DEFINED."""
        df, meta, expected = load_fixture_with_meta("c0208", "happy_metabolite")
        result = classify_analyte_column(df, meta)
        assert result["a8_state"] == expected["a8_state"]
        assert result["pass"] == expected["pass"]
        assert meta.get('a8_state') in ['SINGLE-DRUG','MULTI-CMT-DEFINED','DDI-VICTIM-ONLY','DDI-VICTIM-PERPETRATOR','METABOLITE-DEFINED','CMT-POLICY-MISSING']

    def test_happy_cmt_missing(self, load_fixture_with_meta):
        """다약물인데 cmt_map 없음 → CMT-POLICY-MISSING, Q09."""
        df, meta, expected = load_fixture_with_meta("c0208", "happy_cmt_missing")
        result = classify_analyte_column(df, meta)
        assert result["a8_state"] == expected["a8_state"]
        assert result["pass"] == expected["pass"]
        assert result["route_to_q"] == "Q09"
        assert meta.get('a8_state') in ['SINGLE-DRUG','MULTI-CMT-DEFINED','DDI-VICTIM-ONLY','DDI-VICTIM-PERPETRATOR','METABOLITE-DEFINED','CMT-POLICY-MISSING']

    # --- 1 edge ---

    def test_edge_minimal(self, load_fixture_with_meta):
        """최소 1행, analyte_label 없음 → SINGLE-DRUG (기본값)."""
        df, meta, expected = load_fixture_with_meta("c0208", "edge_minimal")
        result = classify_analyte_column(df, meta)
        assert result["a8_state"] == expected["a8_state"]
        assert result["pass"] == expected["pass"]
        assert meta.get('a8_state') in ['SINGLE-DRUG','MULTI-CMT-DEFINED','DDI-VICTIM-ONLY','DDI-VICTIM-PERPETRATOR','METABOLITE-DEFINED','CMT-POLICY-MISSING']

    # --- 6 category traps ---

    def test_trap_looks_multi_is_single(self, load_fixture_with_meta):
        """다수 행이지만 analyte 1종 → SINGLE-DRUG."""
        df, meta, expected = load_fixture_with_meta("c0208", "trap_looks_multi_is_single")
        result = classify_analyte_column(df, meta)
        assert result["a8_state"] == expected["a8_state"]

    def test_trap_looks_single_is_multi(self, load_fixture_with_meta):
        """analyte 1종이지만 경로 2종(IV/PO) + cmt_map → MULTI-CMT-DEFINED."""
        df, meta, expected = load_fixture_with_meta("c0208", "trap_looks_single_is_multi")
        result = classify_analyte_column(df, meta)
        assert result["a8_state"] == expected["a8_state"]

    def test_trap_looks_ddi_is_metabolite(self, load_fixture_with_meta):
        """2 analyte인데 DDI가 아니라 metabolite → METABOLITE-DEFINED."""
        df, meta, expected = load_fixture_with_meta("c0208", "trap_looks_ddi_is_metabolite")
        result = classify_analyte_column(df, meta)
        assert result["a8_state"] == expected["a8_state"]

    def test_trap_looks_metabolite_is_ddi(self, load_fixture_with_meta):
        """parent_metabolite_map 있지만 study_type=DDI → DDI 우선."""
        df, meta, expected = load_fixture_with_meta("c0208", "trap_looks_metabolite_is_ddi")
        result = classify_analyte_column(df, meta)
        assert result["a8_state"] == expected["a8_state"]

    def test_trap_looks_victim_perp_is_victim_only(self, load_fixture_with_meta):
        """perpetrator_analytes 정의됐지만 df에 해당 analyte 없음 → DDI-VICTIM-ONLY."""
        df, meta, expected = load_fixture_with_meta("c0208", "trap_looks_victim_perp_is_victim_only")
        result = classify_analyte_column(df, meta)
        assert result["a8_state"] == expected["a8_state"]

    def test_trap_looks_defined_is_missing(self, load_fixture_with_meta):
        """cmt_map 키 존재하지만 빈 dict → CMT-POLICY-MISSING, Q09."""
        df, meta, expected = load_fixture_with_meta("c0208", "trap_looks_defined_is_missing")
        result = classify_analyte_column(df, meta)
        assert result["a8_state"] == expected["a8_state"]
        assert result["route_to_q"] == "Q09"

    # --- 1 Q09 routing trap ---

    def test_trap_q09_routing(self, load_fixture_with_meta):
        """3 약물, 3 경로, cmt_map 없음 → CMT-POLICY-MISSING + Q09."""
        df, meta, expected = load_fixture_with_meta("c0208", "trap_q09_routing")
        result = classify_analyte_column(df, meta)
        assert result["a8_state"] == "CMT-POLICY-MISSING"
        assert result["pass"] is False
        assert result["route_to_q"] == "Q09"


class TestC0206:
    """c0206 — A6 이벤트 행 분류 평가 (CLASSIFY ROW_ORDERING)

    postcondition_predicate:
        meta.get('a6_state') in ['SEPARABLE','SAME-TIME-RESOLVABLE','COVARIATE-CHANGE','RESET-NEEDED','URINE-INTERVAL','AMBIGUOUS']

    srp_intent: CLASSIFY ROW_ORDERING
    kind: detect
    can_route_to_q: [Q03, Q04]   (route_to_q ∈ {None, Q03, Q04})
    verify_visualization:
        pass_route_to: c0207
        fail_route_to: Q04
    routing (q_codes SSOT, llm_prompt 산문 비사용):
        Q04 = A6 = AMBIGUOUS (자기축; Q04의 A4=INFUSION-STOP-RESTART disjunct는 c0204 소관, scope 밖)
        Q03 = a0_state=='AIC-POPPK' AND occasion_partition_rule 미기재 (교차축; a0_state는 c0200 생산, read-only)
        동시 충족 시 Q04 우선. a6_state는 6-state 전수 분류 유지. (issues/provenance_gaps.md GAP-10)
    """

    # --- 6 happy (one per a6_state) ---

    def test_happy_separable(self, load_fixture_with_meta):
        """행이 시점별로 분리됨 → SEPARABLE, pass(→c0207)."""
        df, meta, expected = load_fixture_with_meta("c0206", "happy_separable")
        result = classify_row_ordering(df, meta)
        assert result["a6_state"] == expected["a6_state"]
        assert result["pass"] == expected["pass"]
        assert result["route_to_q"] == expected["route_to_q"]
        assert meta.get('a6_state') in ['SEPARABLE','SAME-TIME-RESOLVABLE','COVARIATE-CHANGE','RESET-NEEDED','URINE-INTERVAL','AMBIGUOUS']

    def test_happy_same_time_resolvable(self, load_fixture_with_meta):
        """동일 (ID,TIME) dose+obs 동시각 → SAME-TIME-RESOLVABLE."""
        df, meta, expected = load_fixture_with_meta("c0206", "happy_same_time_resolvable")
        result = classify_row_ordering(df, meta)
        assert result["a6_state"] == expected["a6_state"]
        assert result["pass"] == expected["pass"]
        assert result["route_to_q"] == expected["route_to_q"]
        assert meta.get('a6_state') in ['SEPARABLE','SAME-TIME-RESOLVABLE','COVARIATE-CHANGE','RESET-NEEDED','URINE-INTERVAL','AMBIGUOUS']

    def test_happy_covariate_change(self, load_fixture_with_meta):
        """공변량 변화 이벤트 행 → COVARIATE-CHANGE."""
        df, meta, expected = load_fixture_with_meta("c0206", "happy_covariate_change")
        result = classify_row_ordering(df, meta)
        assert result["a6_state"] == expected["a6_state"]
        assert result["pass"] == expected["pass"]
        assert result["route_to_q"] == expected["route_to_q"]
        assert meta.get('a6_state') in ['SEPARABLE','SAME-TIME-RESOLVABLE','COVARIATE-CHANGE','RESET-NEEDED','URINE-INTERVAL','AMBIGUOUS']

    def test_happy_reset_needed(self, load_fixture_with_meta):
        """reset 이벤트 필요 구조 → RESET-NEEDED."""
        df, meta, expected = load_fixture_with_meta("c0206", "happy_reset_needed")
        result = classify_row_ordering(df, meta)
        assert result["a6_state"] == expected["a6_state"]
        assert result["pass"] == expected["pass"]
        assert result["route_to_q"] == expected["route_to_q"]
        assert meta.get('a6_state') in ['SEPARABLE','SAME-TIME-RESOLVABLE','COVARIATE-CHANGE','RESET-NEEDED','URINE-INTERVAL','AMBIGUOUS']

    def test_happy_urine_interval(self, load_fixture_with_meta):
        """소변 구간 수집 구조 → URINE-INTERVAL."""
        df, meta, expected = load_fixture_with_meta("c0206", "happy_urine_interval")
        result = classify_row_ordering(df, meta)
        assert result["a6_state"] == expected["a6_state"]
        assert result["pass"] == expected["pass"]
        assert result["route_to_q"] == expected["route_to_q"]
        assert meta.get('a6_state') in ['SEPARABLE','SAME-TIME-RESOLVABLE','COVARIATE-CHANGE','RESET-NEEDED','URINE-INTERVAL','AMBIGUOUS']

    def test_happy_ambiguous(self, load_fixture_with_meta):
        """row 유형 모호 → AMBIGUOUS, fail(→Q04)."""
        df, meta, expected = load_fixture_with_meta("c0206", "happy_ambiguous")
        result = classify_row_ordering(df, meta)
        assert result["a6_state"] == expected["a6_state"]
        assert result["pass"] == expected["pass"]
        assert result["route_to_q"] == "Q04"
        assert meta.get('a6_state') in ['SEPARABLE','SAME-TIME-RESOLVABLE','COVARIATE-CHANGE','RESET-NEEDED','URINE-INTERVAL','AMBIGUOUS']

    # --- 2 edge (df fallback, descriptor 부재) ---

    def test_edge_minimal_separable(self, load_fixture_with_meta):
        """최소 1행, descriptor 없음 → df fallback SEPARABLE."""
        df, meta, expected = load_fixture_with_meta("c0206", "edge_minimal_separable")
        result = classify_row_ordering(df, meta)
        assert result["a6_state"] == expected["a6_state"]
        assert result["pass"] == expected["pass"]
        assert meta.get('a6_state') in ['SEPARABLE','SAME-TIME-RESOLVABLE','COVARIATE-CHANGE','RESET-NEEDED','URINE-INTERVAL','AMBIGUOUS']

    def test_edge_df_same_time_fallback(self, load_fixture_with_meta):
        """descriptor 없음 + df 동시각 dose+obs → fallback SAME-TIME-RESOLVABLE."""
        df, meta, expected = load_fixture_with_meta("c0206", "edge_df_same_time_fallback")
        result = classify_row_ordering(df, meta)
        assert result["a6_state"] == expected["a6_state"]
        assert result["pass"] == expected["pass"]
        assert meta.get('a6_state') in ['SEPARABLE','SAME-TIME-RESOLVABLE','COVARIATE-CHANGE','RESET-NEEDED','URINE-INTERVAL','AMBIGUOUS']

    # --- 6 category traps (a6_state별 오분류 차단) ---

    def test_trap_separable(self, load_fixture_with_meta):
        """근접하나 서로 다른 시점(0.0 vs 0.5) → SEPARABLE (SAME-TIME 과대분류 금지)."""
        df, meta, expected = load_fixture_with_meta("c0206", "trap_separable")
        result = classify_row_ordering(df, meta)
        assert result["a6_state"] == expected["a6_state"]

    def test_trap_same_time_resolvable(self, load_fixture_with_meta):
        """동일 (ID,TIME) dose+obs를 descriptor 없이도 SEPARABLE로 silent 격하 금지 → SAME-TIME-RESOLVABLE."""
        df, meta, expected = load_fixture_with_meta("c0206", "trap_same_time_resolvable")
        result = classify_row_ordering(df, meta)
        assert result["a6_state"] == expected["a6_state"]

    def test_trap_covariate_change(self, load_fixture_with_meta):
        """surface는 분리형이나 descriptor=covariate-change → COVARIATE-CHANGE (SEPARABLE 격하 금지)."""
        df, meta, expected = load_fixture_with_meta("c0206", "trap_covariate_change")
        result = classify_row_ordering(df, meta)
        assert result["a6_state"] == expected["a6_state"]

    def test_trap_reset_needed(self, load_fixture_with_meta):
        """descriptor=reset-needed → RESET-NEEDED (SEPARABLE 격하 금지)."""
        df, meta, expected = load_fixture_with_meta("c0206", "trap_reset_needed")
        result = classify_row_ordering(df, meta)
        assert result["a6_state"] == expected["a6_state"]

    def test_trap_urine_interval(self, load_fixture_with_meta):
        """descriptor=urine-interval → URINE-INTERVAL (SEPARABLE 격하 금지)."""
        df, meta, expected = load_fixture_with_meta("c0206", "trap_urine_interval")
        result = classify_row_ordering(df, meta)
        assert result["a6_state"] == expected["a6_state"]

    def test_trap_ambiguous(self, load_fixture_with_meta):
        """surface는 깨끗하나 descriptor=ambiguous → AMBIGUOUS+Q04 (SEPARABLE silent-pass 금지)."""
        df, meta, expected = load_fixture_with_meta("c0206", "trap_ambiguous")
        result = classify_row_ordering(df, meta)
        assert result["a6_state"] == expected["a6_state"]
        assert result["route_to_q"] == "Q04"

    # --- 2 routing traps (per-Q, c0205 Q01/Q15D 선례) ---

    def test_trap_q04_routing(self, load_fixture_with_meta):
        """A6=AMBIGUOUS → fail, route Q04 (명시 routing assert)."""
        df, meta, expected = load_fixture_with_meta("c0206", "trap_q04_routing")
        result = classify_row_ordering(df, meta)
        assert result["a6_state"] == "AMBIGUOUS"
        assert result["pass"] is False
        assert result["route_to_q"] == "Q04"

    def test_trap_q03_routing(self, load_fixture_with_meta):
        """a0_state=AIC-POPPK + occasion_partition_rule 부재 + non-ambiguous → fail, route Q03."""
        df, meta, expected = load_fixture_with_meta("c0206", "trap_q03_routing")
        result = classify_row_ordering(df, meta)
        assert result["a6_state"] == "SEPARABLE"
        assert result["pass"] is False
        assert result["route_to_q"] == "Q03"


class TestC0207:
    """c0207 — A7 공변량 부착 평가 (CLASSIFY COVARIATE_LAYOUT)

    postcondition_predicate:
        meta.get('a7_state') in ['NONE-REQUIRED','BASELINE-CLEAN','BASELINE-IMPUTABLE','TIME-VARYING','EXTERNAL-JOIN','PEDIATRIC-MATURATION','KEY-MISSING','POLICY-MISSING']

    srp_intent: CLASSIFY COVARIATE_LAYOUT
    kind: detect
    can_route_to_q: [Q07, Q13]   (route_to_q ∈ {None, Q07, Q13})
    verify_visualization:
        pass_route_to: c0208
        fail_route_to: Q07
    routing (q_codes SSOT, llm_prompt 산문 비사용):
        Q07 = A7 = POLICY-MISSING (자기축)
        Q13 = A7 = KEY-MISSING   (자기축; c0206 Q03 같은 교차축 trigger 없음)
        나머지 6 state → route_to_q=None, pass=True.
    선언 1차(meta['covariate_state']) → df fallback 3-outcome
    (cov 없음→NONE-REQUIRED / cov+결측→BASELINE-IMPUTABLE / cov+무결측→BASELINE-CLEAN).
    df만으로 Q07/Q13 날조 금지. (issues/provenance_gaps.md GAP-11; GAP-3 유지: a7_state만 emit)
    """

    # --- 8 happy (one per a7_state) ---

    def test_happy_none_required(self, load_fixture_with_meta):
        """공변량 불요 선언 → NONE-REQUIRED, pass(→c0208)."""
        df, meta, expected = load_fixture_with_meta("c0207", "happy_none_required")
        result = classify_covariate_layout(df, meta)
        assert result["a7_state"] == expected["a7_state"]
        assert result["pass"] == expected["pass"]
        assert result["route_to_q"] == expected["route_to_q"]
        assert result["route_to_q"] is None  # verify_visualization pass → c0208
        assert meta.get('a7_state') in ['NONE-REQUIRED','BASELINE-CLEAN','BASELINE-IMPUTABLE','TIME-VARYING','EXTERNAL-JOIN','PEDIATRIC-MATURATION','KEY-MISSING','POLICY-MISSING']

    def test_happy_baseline_clean(self, load_fixture_with_meta):
        """기저 공변량 존재·무결측 → BASELINE-CLEAN."""
        df, meta, expected = load_fixture_with_meta("c0207", "happy_baseline_clean")
        result = classify_covariate_layout(df, meta)
        assert result["a7_state"] == expected["a7_state"]
        assert result["pass"] == expected["pass"]
        assert result["route_to_q"] == expected["route_to_q"]
        assert meta.get('a7_state') in ['NONE-REQUIRED','BASELINE-CLEAN','BASELINE-IMPUTABLE','TIME-VARYING','EXTERNAL-JOIN','PEDIATRIC-MATURATION','KEY-MISSING','POLICY-MISSING']

    def test_happy_baseline_imputable(self, load_fixture_with_meta):
        """기저 공변량 결측 존재(imputation 정책 有) → BASELINE-IMPUTABLE."""
        df, meta, expected = load_fixture_with_meta("c0207", "happy_baseline_imputable")
        result = classify_covariate_layout(df, meta)
        assert result["a7_state"] == expected["a7_state"]
        assert result["pass"] == expected["pass"]
        assert result["route_to_q"] == expected["route_to_q"]
        assert meta.get('a7_state') in ['NONE-REQUIRED','BASELINE-CLEAN','BASELINE-IMPUTABLE','TIME-VARYING','EXTERNAL-JOIN','PEDIATRIC-MATURATION','KEY-MISSING','POLICY-MISSING']

    def test_happy_time_varying(self, load_fixture_with_meta):
        """시변 공변량 선언 → TIME-VARYING."""
        df, meta, expected = load_fixture_with_meta("c0207", "happy_time_varying")
        result = classify_covariate_layout(df, meta)
        assert result["a7_state"] == expected["a7_state"]
        assert result["pass"] == expected["pass"]
        assert result["route_to_q"] == expected["route_to_q"]
        assert meta.get('a7_state') in ['NONE-REQUIRED','BASELINE-CLEAN','BASELINE-IMPUTABLE','TIME-VARYING','EXTERNAL-JOIN','PEDIATRIC-MATURATION','KEY-MISSING','POLICY-MISSING']

    def test_happy_external_join(self, load_fixture_with_meta):
        """외부 covariate table join 선언 → EXTERNAL-JOIN."""
        df, meta, expected = load_fixture_with_meta("c0207", "happy_external_join")
        result = classify_covariate_layout(df, meta)
        assert result["a7_state"] == expected["a7_state"]
        assert result["pass"] == expected["pass"]
        assert result["route_to_q"] == expected["route_to_q"]
        assert meta.get('a7_state') in ['NONE-REQUIRED','BASELINE-CLEAN','BASELINE-IMPUTABLE','TIME-VARYING','EXTERNAL-JOIN','PEDIATRIC-MATURATION','KEY-MISSING','POLICY-MISSING']

    def test_happy_pediatric_maturation(self, load_fixture_with_meta):
        """소아 maturation 공변량 선언 → PEDIATRIC-MATURATION."""
        df, meta, expected = load_fixture_with_meta("c0207", "happy_pediatric_maturation")
        result = classify_covariate_layout(df, meta)
        assert result["a7_state"] == expected["a7_state"]
        assert result["pass"] == expected["pass"]
        assert result["route_to_q"] == expected["route_to_q"]
        assert meta.get('a7_state') in ['NONE-REQUIRED','BASELINE-CLEAN','BASELINE-IMPUTABLE','TIME-VARYING','EXTERNAL-JOIN','PEDIATRIC-MATURATION','KEY-MISSING','POLICY-MISSING']

    def test_happy_key_missing(self, load_fixture_with_meta):
        """외부 join key 모호 → KEY-MISSING, fail(→Q13)."""
        df, meta, expected = load_fixture_with_meta("c0207", "happy_key_missing")
        result = classify_covariate_layout(df, meta)
        assert result["a7_state"] == expected["a7_state"]
        assert result["pass"] == expected["pass"]
        assert result["route_to_q"] == "Q13"
        assert meta.get('a7_state') in ['NONE-REQUIRED','BASELINE-CLEAN','BASELINE-IMPUTABLE','TIME-VARYING','EXTERNAL-JOIN','PEDIATRIC-MATURATION','KEY-MISSING','POLICY-MISSING']

    def test_happy_policy_missing(self, load_fixture_with_meta):
        """imputation 정책 부재 → POLICY-MISSING, fail(→Q07 = verify_visualization fail_route_to)."""
        df, meta, expected = load_fixture_with_meta("c0207", "happy_policy_missing")
        result = classify_covariate_layout(df, meta)
        assert result["a7_state"] == expected["a7_state"]
        assert result["pass"] == expected["pass"]
        assert result["route_to_q"] == "Q07"
        assert meta.get('a7_state') in ['NONE-REQUIRED','BASELINE-CLEAN','BASELINE-IMPUTABLE','TIME-VARYING','EXTERNAL-JOIN','PEDIATRIC-MATURATION','KEY-MISSING','POLICY-MISSING']

    # --- 3 edge (df fallback, descriptor 부재) ---

    def test_edge_minimal_none_required(self, load_fixture_with_meta):
        """descriptor 없음 + cov 컬럼 없음 → df fallback NONE-REQUIRED."""
        df, meta, expected = load_fixture_with_meta("c0207", "edge_minimal_none_required")
        result = classify_covariate_layout(df, meta)
        assert result["a7_state"] == expected["a7_state"]
        assert result["pass"] == expected["pass"]
        assert result["route_to_q"] is None
        assert meta.get('a7_state') in ['NONE-REQUIRED','BASELINE-CLEAN','BASELINE-IMPUTABLE','TIME-VARYING','EXTERNAL-JOIN','PEDIATRIC-MATURATION','KEY-MISSING','POLICY-MISSING']

    def test_edge_df_baseline_clean_fallback(self, load_fixture_with_meta):
        """descriptor 없음 + cov 무결측 → df fallback BASELINE-CLEAN."""
        df, meta, expected = load_fixture_with_meta("c0207", "edge_df_baseline_clean_fallback")
        result = classify_covariate_layout(df, meta)
        assert result["a7_state"] == expected["a7_state"]
        assert result["pass"] == expected["pass"]
        assert meta.get('a7_state') in ['NONE-REQUIRED','BASELINE-CLEAN','BASELINE-IMPUTABLE','TIME-VARYING','EXTERNAL-JOIN','PEDIATRIC-MATURATION','KEY-MISSING','POLICY-MISSING']

    def test_edge_df_baseline_imputable_fallback(self, load_fixture_with_meta):
        """descriptor 없음 + cov 결측 존재 → df fallback BASELINE-IMPUTABLE."""
        df, meta, expected = load_fixture_with_meta("c0207", "edge_df_baseline_imputable_fallback")
        result = classify_covariate_layout(df, meta)
        assert result["a7_state"] == expected["a7_state"]
        assert result["pass"] == expected["pass"]
        assert meta.get('a7_state') in ['NONE-REQUIRED','BASELINE-CLEAN','BASELINE-IMPUTABLE','TIME-VARYING','EXTERNAL-JOIN','PEDIATRIC-MATURATION','KEY-MISSING','POLICY-MISSING']

    # --- 8 category traps (a7_state별 오분류 차단; declaration이 df surface를 이김) ---

    def test_trap_none_required(self, load_fixture_with_meta):
        """df에 깨끗한 cov 존재(fallback CLEAN)지만 선언 none-required → NONE-REQUIRED."""
        df, meta, expected = load_fixture_with_meta("c0207", "trap_none_required")
        result = classify_covariate_layout(df, meta)
        assert result["a7_state"] == expected["a7_state"]

    def test_trap_baseline_clean(self, load_fixture_with_meta):
        """df 결측 존재(fallback IMPUTABLE)지만 선언 baseline-clean → BASELINE-CLEAN (격하 금지)."""
        df, meta, expected = load_fixture_with_meta("c0207", "trap_baseline_clean")
        result = classify_covariate_layout(df, meta)
        assert result["a7_state"] == expected["a7_state"]

    def test_trap_baseline_imputable(self, load_fixture_with_meta):
        """df 무결측(fallback CLEAN)지만 선언 baseline-imputable → BASELINE-IMPUTABLE (silent CLEAN 금지)."""
        df, meta, expected = load_fixture_with_meta("c0207", "trap_baseline_imputable")
        result = classify_covariate_layout(df, meta)
        assert result["a7_state"] == expected["a7_state"]

    def test_trap_time_varying(self, load_fixture_with_meta):
        """baseline처럼 보이나 선언 time-varying → TIME-VARYING (BASELINE 격하 금지)."""
        df, meta, expected = load_fixture_with_meta("c0207", "trap_time_varying")
        result = classify_covariate_layout(df, meta)
        assert result["a7_state"] == expected["a7_state"]

    def test_trap_external_join(self, load_fixture_with_meta):
        """df에 cov 없음(fallback NONE-REQUIRED)지만 선언 external-join → EXTERNAL-JOIN (격하 금지)."""
        df, meta, expected = load_fixture_with_meta("c0207", "trap_external_join")
        result = classify_covariate_layout(df, meta)
        assert result["a7_state"] == expected["a7_state"]

    def test_trap_pediatric_maturation(self, load_fixture_with_meta):
        """AGE+WT 깨끗(fallback BASELINE-CLEAN)지만 선언 pediatric-maturation → PEDIATRIC-MATURATION."""
        df, meta, expected = load_fixture_with_meta("c0207", "trap_pediatric_maturation")
        result = classify_covariate_layout(df, meta)
        assert result["a7_state"] == expected["a7_state"]

    def test_trap_key_missing(self, load_fixture_with_meta):
        """df fallback이면 NONE-REQUIRED(pass)이나 선언 key-missing → KEY-MISSING+Q13 (silent-pass 금지)."""
        df, meta, expected = load_fixture_with_meta("c0207", "trap_key_missing")
        result = classify_covariate_layout(df, meta)
        assert result["a7_state"] == expected["a7_state"]
        assert result["route_to_q"] == "Q13"

    def test_trap_policy_missing(self, load_fixture_with_meta):
        """df 결측→fallback IMPUTABLE(pass)이나 선언 policy-missing → POLICY-MISSING+Q07 (★silent-pass 금지)."""
        df, meta, expected = load_fixture_with_meta("c0207", "trap_policy_missing")
        result = classify_covariate_layout(df, meta)
        assert result["a7_state"] == expected["a7_state"]
        assert result["route_to_q"] == "Q07"

    # --- 2 routing traps (per-Q, c0205 Q01/Q15D · c0206 Q04/Q03 선례) ---

    def test_trap_q07_routing(self, load_fixture_with_meta):
        """A7=POLICY-MISSING → fail, route Q07 (명시 routing assert)."""
        df, meta, expected = load_fixture_with_meta("c0207", "trap_q07_routing")
        result = classify_covariate_layout(df, meta)
        assert result["a7_state"] == "POLICY-MISSING"
        assert result["pass"] is False
        assert result["route_to_q"] == "Q07"

    def test_trap_q13_routing(self, load_fixture_with_meta):
        """A7=KEY-MISSING → fail, route Q13 (명시 routing assert)."""
        df, meta, expected = load_fixture_with_meta("c0207", "trap_q13_routing")
        result = classify_covariate_layout(df, meta)
        assert result["a7_state"] == "KEY-MISSING"
        assert result["pass"] is False
        assert result["route_to_q"] == "Q13"


class TestC0013:
    """c0013 — CMT 부여 (ASSIGN CMT)

    postcondition_predicate:
        'CMT' in df.columns and (df.loc[df['EVID'].isin([0,1,3,4]), 'CMT'] > 0).all() and df['CMT'].apply(lambda x: isinstance(x, (int, np.integer)) and x > 0 if pd.notna(x) else True).all()

    srp_intent: ASSIGN CMT
    kind: transform
    requires_detection_by: c0208
    can_route_to_q: [Q09]
    """

    def _check_postcond(self, df_out):
        assert 'CMT' in df_out.columns and (df_out.loc[df_out['EVID'].isin([0,1,3,4]), 'CMT'] > 0).all() and df_out['CMT'].apply(lambda x: isinstance(x, (int, np.integer)) and x > 0 if pd.notna(x) else True).all()

    # --- 3 happy ---

    def test_happy_single(self, load_fixture_with_meta):
        """SINGLE-DRUG: dose(EVID 1,4)→CMT=1, obs(EVID 0)→CMT=2."""
        df, meta, expected = load_fixture_with_meta("c0013", "happy_single")
        result = assign_cmt(df, meta)
        assert result["success"] == expected["success"]
        df_out = result["df"]
        self._check_postcond(df_out)
        assert list(df_out["CMT"]) == expected["CMT"]

    def test_happy_multi(self, load_fixture_with_meta):
        """MULTI-CMT-DEFINED: cmt_map으로 analyte별 CMT 매핑."""
        df, meta, expected = load_fixture_with_meta("c0013", "happy_multi")
        result = assign_cmt(df, meta)
        assert result["success"] == expected["success"]
        df_out = result["df"]
        self._check_postcond(df_out)
        assert list(df_out["CMT"]) == expected["CMT"]

    def test_happy_metabolite(self, load_fixture_with_meta):
        """METABOLITE-DEFINED: parent/metabolite별 CMT 매핑."""
        df, meta, expected = load_fixture_with_meta("c0013", "happy_metabolite")
        result = assign_cmt(df, meta)
        assert result["success"] == expected["success"]
        df_out = result["df"]
        self._check_postcond(df_out)
        assert list(df_out["CMT"]) == expected["CMT"]

    def test_happy_ddi_victim_only(self, load_fixture_with_meta):
        """DDI-VICTIM-ONLY: victim 단일 약물, dose→CMT=1, obs→CMT=2."""
        df, meta, expected = load_fixture_with_meta("c0013", "happy_ddi_victim_only")
        result = assign_cmt(df, meta)
        assert result["success"] == expected["success"]
        df_out = result["df"]
        self._check_postcond(df_out)
        assert list(df_out["CMT"]) == expected["CMT"]

    def test_happy_ddi_perp(self, load_fixture_with_meta):
        """DDI-VICTIM-PERPETRATOR: victim+perpetrator를 cmt_map으로 analyte별 CMT 매핑."""
        df, meta, expected = load_fixture_with_meta("c0013", "happy_ddi_perp")
        result = assign_cmt(df, meta)
        assert result["success"] == expected["success"]
        df_out = result["df"]
        self._check_postcond(df_out)
        assert list(df_out["CMT"]) == expected["CMT"]

    # --- 1 edge ---

    def test_edge_single_obs(self, load_fixture_with_meta):
        """최소 1행 obs, SINGLE-DRUG → CMT=[2]."""
        df, meta, expected = load_fixture_with_meta("c0013", "edge_single_obs")
        result = assign_cmt(df, meta)
        assert result["success"] == expected["success"]
        df_out = result["df"]
        self._check_postcond(df_out)
        assert list(df_out["CMT"]) == expected["CMT"]

    # --- 3 traps ---

    def test_trap_no_evid(self, load_fixture_with_meta):
        """EVID 컬럼 부재 → fail, Q09."""
        df, meta, expected = load_fixture_with_meta("c0013", "trap_no_evid")
        result = assign_cmt(df, meta)
        assert result["success"] == expected["success"]
        assert result["route_to_q"] == expected["route_to_q"]

    def test_trap_policy_missing(self, load_fixture_with_meta):
        """a8_state=CMT-POLICY-MISSING → fail, Q09."""
        df, meta, expected = load_fixture_with_meta("c0013", "trap_policy_missing")
        result = assign_cmt(df, meta)
        assert result["success"] == expected["success"]
        assert result["route_to_q"] == "Q09"

    def test_trap_unmapped_analyte(self, load_fixture_with_meta):
        """MULTI-CMT인데 analyte가 cmt_map에 없음 → fail, Q09."""
        df, meta, expected = load_fixture_with_meta("c0013", "trap_unmapped_analyte")
        result = assign_cmt(df, meta)
        assert result["success"] == expected["success"]
        assert result["route_to_q"] == "Q09"


class TestC0015:
    """c0015 — ADDL 부여 (ASSIGN ADDL)

    postcondition_predicate:
        'ADDL' in df.columns and (df['ADDL'] >= 0).all() and df['ADDL'].apply(lambda x: isinstance(x, (int, np.integer))).all()

    srp_intent: ASSIGN ADDL
    kind: transform
    requires_detection_by: c0010
    can_route_to_q: [Q14]
    """

    def _check_postcond(self, df):
        assert 'ADDL' in df.columns and (df['ADDL'] >= 0).all() and df['ADDL'].apply(lambda x: isinstance(x, (int, np.integer))).all()

    # --- 1 happy ---

    def test_happy(self, load_fixture_with_meta):
        """등간격 동일 dose 3회(@0/24/48) 압축 → 첫 행 ADDL=2, obs ADDL=0, 반복 dose 행 제거."""
        df, meta, expected = load_fixture_with_meta("c0015", "happy")
        result = assign_addl(df, meta)
        assert result["success"] == expected["success"]
        df_out = result["df"]
        self._check_postcond(df_out)
        assert list(df_out["ADDL"]) == expected["ADDL"]

    # --- 1 edge ---

    def test_edge(self, load_fixture_with_meta):
        """반복 없는 단일 dose + obs → 모든 ADDL=0, 행 보존."""
        df, meta, expected = load_fixture_with_meta("c0015", "edge")
        result = assign_addl(df, meta)
        assert result["success"] == expected["success"]
        df_out = result["df"]
        self._check_postcond(df_out)
        assert list(df_out["ADDL"]) == expected["ADDL"]

    # --- 3 traps ---

    def test_trap_unequal_interval(self, load_fixture_with_meta):
        """불규칙 간격 dose(@0/24/50) → 압축 금지, 모든 ADDL=0, 행 수 보존."""
        df, meta, expected = load_fixture_with_meta("c0015", "trap_unequal_interval")
        result = assign_addl(df, meta)
        assert result["success"] == expected["success"]
        df_out = result["df"]
        self._check_postcond(df_out)
        assert list(df_out["ADDL"]) == expected["ADDL"]

    def test_trap_no_evid(self, load_fixture_with_meta):
        """EVID 컬럼 부재 — 선행조건 위반 → fail."""
        df, meta, expected = load_fixture_with_meta("c0015", "trap_no_evid")
        result = assign_addl(df, meta)
        assert result["success"] == expected["success"]

    def test_trap_conflict(self, load_fixture_with_meta):
        """A4=ADDL-ACTUAL-CONFLICT → fail, Q14."""
        df, meta, expected = load_fixture_with_meta("c0015", "trap_conflict")
        result = assign_addl(df, meta)
        assert result["success"] == expected["success"]
        assert result["route_to_q"] == "Q14"


class TestC0016:
    """c0016 — II 부여 (ASSIGN II)

    postcondition_predicate:
        'II' in df.columns and (df.loc[df['ADDL'] > 0, 'II'] > 0).all() and (df.loc[df['ADDL'] == 0, 'II'] == 0).all()

    srp_intent: ASSIGN II
    kind: transform
    requires_detection_by: c0015
    can_route_to_q: [Q14]
    """

    def _check_postcond(self, df):
        assert 'II' in df.columns and (df.loc[df['ADDL'] > 0, 'II'] > 0).all() and (df.loc[df['ADDL'] == 0, 'II'] == 0).all()

    # --- 1 happy ---

    def test_happy(self, load_fixture):
        """ADDL>0(=3) 행 → II=등간격(12), ADDL=0 행 → II=0."""
        df_in, expected = load_fixture("c0016", "happy")
        result = assign_ii(df_in)
        assert result["success"] == expected["success"]
        df_out = result["df"]
        self._check_postcond(df_out)
        assert list(df_out["II"]) == expected["II"]

    # --- 1 edge ---

    def test_edge(self, load_fixture):
        """반복 없음(전부 ADDL=0) → 모든 II=0."""
        df_in, expected = load_fixture("c0016", "edge")
        result = assign_ii(df_in)
        assert result["success"] == expected["success"]
        df_out = result["df"]
        self._check_postcond(df_out)
        assert list(df_out["II"]) == expected["II"]

    # --- 4 traps ---

    def test_trap_addl_no_interval(self, load_fixture):
        """ADDL>0인데 dose_interval 결측 → II=NaN silent 통과 금지, Q14."""
        df_in, expected = load_fixture("c0016", "trap_addl_no_interval")
        result = assign_ii(df_in)
        assert result["success"] == expected["success"]
        assert result["route_to_q"] == expected["route_to_q"]

    def test_trap_addl_zero_interval(self, load_fixture):
        """ADDL>0인데 dose_interval=0 → ADDL>0⟹II>0 위반, Q14."""
        df_in, expected = load_fixture("c0016", "trap_addl_zero_interval")
        result = assign_ii(df_in)
        assert result["success"] == expected["success"]
        assert result["route_to_q"] == expected["route_to_q"]

    def test_trap_zero_addl_has_interval(self, load_fixture):
        """ADDL=0인데 dose_interval=24 → II는 반드시 0(ADDL==0⟹II==0)."""
        df_in, expected = load_fixture("c0016", "trap_zero_addl_has_interval")
        result = assign_ii(df_in)
        assert result["success"] == expected["success"]
        df_out = result["df"]
        self._check_postcond(df_out)
        assert list(df_out["II"]) == expected["II"]

    def test_trap_no_addl(self, load_fixture):
        """ADDL 컬럼 부재(c0015 미통과) → hard fail."""
        df_in, expected = load_fixture("c0016", "trap_no_addl")
        result = assign_ii(df_in)
        assert result["success"] == expected["success"]


class TestC0017:
    """c0017 — DV 부여 (ASSIGN DV)

    postcondition_predicate:
        'DV' in df.columns and not ((df['EVID']==0) & (df['MDV']==0) & (df['DV'].isna())).any()

    srp_intent: ASSIGN DV
    kind: transform
    requires_detection_by: c0011
    can_route_to_q: []
    """

    def _check_postcond(self, df):
        assert 'DV' in df.columns and not ((df['EVID']==0) & (df['MDV']==0) & (df['DV'].isna())).any()

    # --- 1 happy ---

    def test_happy(self, load_fixture):
        """dose(MDV=1)→DV=0, 유효 obs(EVID=0,MDV=0)→측정값, BLQ obs(MDV=1)→0."""
        df_in, expected = load_fixture("c0017", "happy")
        result = assign_dv(df_in)
        assert result["success"] == expected["success"]
        df_out = result["df"]
        self._check_postcond(df_out)
        assert list(df_out["DV"]) == expected["DV"]

    # --- 1 edge ---

    def test_edge(self, load_fixture):
        """관측 없음(전부 MDV=1) → 모든 DV=0."""
        df_in, expected = load_fixture("c0017", "edge")
        result = assign_dv(df_in)
        assert result["success"] == expected["success"]
        df_out = result["df"]
        self._check_postcond(df_out)
        assert list(df_out["DV"]) == expected["DV"]

    # --- 2 traps ---

    def test_trap_obs_missing(self, load_fixture):
        """유효 obs(EVID=0,MDV=0)인데 dv_value 결측 → DV NaN, postcond 위반 → fail."""
        df_in, expected = load_fixture("c0017", "trap_obs_missing")
        result = assign_dv(df_in)
        assert result["success"] == expected["success"]

    def test_trap_col(self, load_fixture):
        """MDV 컬럼 부재 → fail."""
        df_in, expected = load_fixture("c0017", "trap_col")
        result = assign_dv(df_in)
        assert result["success"] == expected["success"]


class TestC0018:
    """c0018 — ID 정수화 (ASSIGN ID)

    postcondition_predicate:
        'ID' in df.columns and (df['ID'] > 0).all() and df['ID'].apply(lambda x: isinstance(x, (int, np.integer))).all()

    srp_intent: ASSIGN ID
    kind: transform
    requires_detection_by: c0001
    can_route_to_q: []
    """

    def _check_postcond(self, df):
        assert 'ID' in df.columns and (df['ID'] > 0).all() and df['ID'].apply(lambda x: isinstance(x, (int, np.integer))).all()

    # --- 1 happy ---

    def test_happy(self, load_fixture):
        """문자열 subject_id(PT-001 반복, PT-002) → 양의 정수 ID=[1,1,2]."""
        df_in, expected = load_fixture("c0018", "happy")
        result = assign_id(df_in)
        assert result["success"] == expected["success"]
        df_out = result["df"]
        self._check_postcond(df_out)
        assert list(df_out["ID"]) == expected["ID"]

    # --- 1 edge ---

    def test_edge(self, load_fixture):
        """숫자 subject_id(5 반복, 단일 subject) → 1부터 재인덱싱, ID=[1,1,1]."""
        df_in, expected = load_fixture("c0018", "edge")
        result = assign_id(df_in)
        assert result["success"] == expected["success"]
        df_out = result["df"]
        self._check_postcond(df_out)
        assert list(df_out["ID"]) == expected["ID"]

    # --- 2 traps ---

    def test_trap_missing_sid(self, load_fixture):
        """subject_id에 결측 행 존재 → ID=0/NaN silent 통과 금지, fail."""
        df_in, expected = load_fixture("c0018", "trap_missing_sid")
        result = assign_id(df_in)
        assert result["success"] == expected["success"]

    def test_trap_col(self, load_fixture):
        """subject_id 컬럼 부재 → fail."""
        df_in, expected = load_fixture("c0018", "trap_col")
        result = assign_id(df_in)
        assert result["success"] == expected["success"]


class TestC0200:
    """c0200 — A0 분석 의도 평가 (VERIFY COLUMN_SCHEMA, ※실제로는 A0 axis classifier)

    postcondition_predicate:
        meta.get('a0_state') in ['AIC-MISSING','AIC-PK','AIC-POPPK','AIC-PKPD','AIC-ER','AIC-DDI','AIC-PEDS','AIC-SPECIAL','AIC-CUSTOM']

    srp_intent: VERIFY COLUMN_SCHEMA
    kind: verify
    can_route_to_q: [Q11]
    verify_visualization:
        pass_route_to: c0201
        fail_route_to: Q11
    """

    # --- 8 happy pass (one per non-missing a0_state) ---

    def test_happy_aic_pk(self, load_fixture_with_meta):
        """endpoint 불필요 intent AIC-PK 선언 → AIC-PK, pass(→c0201)."""
        df, meta, expected = load_fixture_with_meta("c0200", "happy_aic_pk")
        result = verify_a0_analysis_intent(df, meta)
        assert result["a0_state"] == expected["a0_state"]
        assert result["pass"] == expected["pass"]
        assert result["route_to_q"] == expected["route_to_q"]
        assert meta.get('a0_state') in ['AIC-MISSING','AIC-PK','AIC-POPPK','AIC-PKPD','AIC-ER','AIC-DDI','AIC-PEDS','AIC-SPECIAL','AIC-CUSTOM']

    def test_happy_aic_poppk(self, load_fixture_with_meta):
        """AIC-POPPK 선언 → AIC-POPPK."""
        df, meta, expected = load_fixture_with_meta("c0200", "happy_aic_poppk")
        result = verify_a0_analysis_intent(df, meta)
        assert result["a0_state"] == expected["a0_state"]
        assert result["pass"] == expected["pass"]
        assert meta.get('a0_state') in ['AIC-MISSING','AIC-PK','AIC-POPPK','AIC-PKPD','AIC-ER','AIC-DDI','AIC-PEDS','AIC-SPECIAL','AIC-CUSTOM']

    def test_happy_aic_pkpd(self, load_fixture_with_meta):
        """AIC-PKPD + endpoint(CONTINUOUS_PD, 필수) 충족 → AIC-PKPD."""
        df, meta, expected = load_fixture_with_meta("c0200", "happy_aic_pkpd")
        result = verify_a0_analysis_intent(df, meta)
        assert result["a0_state"] == expected["a0_state"]
        assert result["pass"] == expected["pass"]
        assert meta.get('a0_state') in ['AIC-MISSING','AIC-PK','AIC-POPPK','AIC-PKPD','AIC-ER','AIC-DDI','AIC-PEDS','AIC-SPECIAL','AIC-CUSTOM']

    def test_happy_aic_er(self, load_fixture_with_meta):
        """AIC-ER + endpoint(EXPOSURE_METRIC, 필수) 충족 → AIC-ER."""
        df, meta, expected = load_fixture_with_meta("c0200", "happy_aic_er")
        result = verify_a0_analysis_intent(df, meta)
        assert result["a0_state"] == expected["a0_state"]
        assert result["pass"] == expected["pass"]
        assert meta.get('a0_state') in ['AIC-MISSING','AIC-PK','AIC-POPPK','AIC-PKPD','AIC-ER','AIC-DDI','AIC-PEDS','AIC-SPECIAL','AIC-CUSTOM']

    def test_happy_aic_ddi(self, load_fixture_with_meta):
        """AIC-DDI 선언 → AIC-DDI."""
        df, meta, expected = load_fixture_with_meta("c0200", "happy_aic_ddi")
        result = verify_a0_analysis_intent(df, meta)
        assert result["a0_state"] == expected["a0_state"]
        assert result["pass"] == expected["pass"]
        assert meta.get('a0_state') in ['AIC-MISSING','AIC-PK','AIC-POPPK','AIC-PKPD','AIC-ER','AIC-DDI','AIC-PEDS','AIC-SPECIAL','AIC-CUSTOM']

    def test_happy_aic_peds(self, load_fixture_with_meta):
        """AIC-PEDS 선언 → AIC-PEDS."""
        df, meta, expected = load_fixture_with_meta("c0200", "happy_aic_peds")
        result = verify_a0_analysis_intent(df, meta)
        assert result["a0_state"] == expected["a0_state"]
        assert result["pass"] == expected["pass"]
        assert meta.get('a0_state') in ['AIC-MISSING','AIC-PK','AIC-POPPK','AIC-PKPD','AIC-ER','AIC-DDI','AIC-PEDS','AIC-SPECIAL','AIC-CUSTOM']

    def test_happy_aic_special(self, load_fixture_with_meta):
        """AIC-SPECIAL 선언 → AIC-SPECIAL."""
        df, meta, expected = load_fixture_with_meta("c0200", "happy_aic_special")
        result = verify_a0_analysis_intent(df, meta)
        assert result["a0_state"] == expected["a0_state"]
        assert result["pass"] == expected["pass"]
        assert meta.get('a0_state') in ['AIC-MISSING','AIC-PK','AIC-POPPK','AIC-PKPD','AIC-ER','AIC-DDI','AIC-PEDS','AIC-SPECIAL','AIC-CUSTOM']

    def test_happy_aic_custom(self, load_fixture_with_meta):
        """AIC-CUSTOM + policy_document(문서 명시) 충족 → AIC-CUSTOM."""
        df, meta, expected = load_fixture_with_meta("c0200", "happy_aic_custom")
        result = verify_a0_analysis_intent(df, meta)
        assert result["a0_state"] == expected["a0_state"]
        assert result["pass"] == expected["pass"]
        assert meta.get('a0_state') in ['AIC-MISSING','AIC-PK','AIC-POPPK','AIC-PKPD','AIC-ER','AIC-DDI','AIC-PEDS','AIC-SPECIAL','AIC-CUSTOM']

    # --- fail happy: AIC-MISSING ---

    def test_happy_aic_missing(self, load_fixture_with_meta):
        """intent·endpoint 모두 부재 → AIC-MISSING, Q11."""
        df, meta, expected = load_fixture_with_meta("c0200", "happy_aic_missing")
        result = verify_a0_analysis_intent(df, meta)
        assert result["a0_state"] == expected["a0_state"]
        assert result["pass"] == expected["pass"]
        assert result["route_to_q"] == "Q11"
        assert meta.get('a0_state') in ['AIC-MISSING','AIC-PK','AIC-POPPK','AIC-PKPD','AIC-ER','AIC-DDI','AIC-PEDS','AIC-SPECIAL','AIC-CUSTOM']

    # --- edge: endpoint-only fallback (before_after 예시 경로) ---

    def test_edge_endpoint_fallback(self, load_fixture_with_meta):
        """intent 미선언, endpoint=PK_CONCENTRATION → fallback AIC-PK."""
        df, meta, expected = load_fixture_with_meta("c0200", "edge_endpoint_fallback")
        result = verify_a0_analysis_intent(df, meta)
        assert result["a0_state"] == expected["a0_state"]
        assert result["pass"] == expected["pass"]
        assert meta.get('a0_state') in ['AIC-MISSING','AIC-PK','AIC-POPPK','AIC-PKPD','AIC-ER','AIC-DDI','AIC-PEDS','AIC-SPECIAL','AIC-CUSTOM']

    # --- category / misclassification traps ---

    def test_trap_pkpd_missing_endpoint(self, load_fixture_with_meta):
        """AIC-PKPD인데 endpoint(필수) 부재 → 계약 미완성 → AIC-MISSING/Q11."""
        df, meta, expected = load_fixture_with_meta("c0200", "trap_pkpd_missing_endpoint")
        result = verify_a0_analysis_intent(df, meta)
        assert result["a0_state"] == expected["a0_state"]
        assert result["route_to_q"] == "Q11"

    def test_trap_er_out_of_scope_endpoint(self, load_fixture_with_meta):
        """AIC-ER + endpoint가 scope 밖(CATEGORICAL_PD) → AIC-MISSING/Q11."""
        df, meta, expected = load_fixture_with_meta("c0200", "trap_er_out_of_scope_endpoint")
        result = verify_a0_analysis_intent(df, meta)
        assert result["a0_state"] == expected["a0_state"]
        assert result["route_to_q"] == "Q11"

    def test_trap_custom_no_document(self, load_fixture_with_meta):
        """AIC-CUSTOM인데 policy_document(문서) 부재 → AIC-MISSING/Q11."""
        df, meta, expected = load_fixture_with_meta("c0200", "trap_custom_no_document")
        result = verify_a0_analysis_intent(df, meta)
        assert result["a0_state"] == expected["a0_state"]
        assert result["route_to_q"] == "Q11"

    def test_trap_endpoint_without_intent(self, load_fixture_with_meta):
        """intent 미선언이지만 endpoint=CONTINUOUS_PD 존재 → fallback AIC-PKPD (MISSING 아님)."""
        df, meta, expected = load_fixture_with_meta("c0200", "trap_endpoint_without_intent")
        result = verify_a0_analysis_intent(df, meta)
        assert result["a0_state"] == expected["a0_state"]
        assert result["pass"] is True

    def test_trap_unrecognized_intent(self, load_fixture_with_meta):
        """미인정 intent(AIC-FOO) → AIC-MISSING/Q11 (hallucination guard)."""
        df, meta, expected = load_fixture_with_meta("c0200", "trap_unrecognized_intent")
        result = verify_a0_analysis_intent(df, meta)
        assert result["a0_state"] == expected["a0_state"]
        assert result["route_to_q"] == "Q11"

    def test_trap_whitespace_case(self, load_fixture_with_meta):
        """' aic-pk ' (공백·소문자) → 정규화 후 AIC-PK."""
        df, meta, expected = load_fixture_with_meta("c0200", "trap_whitespace_case")
        result = verify_a0_analysis_intent(df, meta)
        assert result["a0_state"] == expected["a0_state"]

    # --- MANDATORY: AIC-MISSING → Q11 routing trap ---

    def test_trap_aic_missing_q11_routing(self, load_fixture_with_meta):
        """공백뿐인 intent는 선언처럼 보이나 사실상 부재 → AIC-MISSING + Q11."""
        df, meta, expected = load_fixture_with_meta("c0200", "trap_aic_missing_q11_routing")
        result = verify_a0_analysis_intent(df, meta)
        assert result["a0_state"] == "AIC-MISSING"
        assert result["pass"] is False
        assert result["route_to_q"] == "Q11"

    # --- 선언이 endpoint fallback을 이김 (AUDIT #2: 선언-직결 state별 override trap) ---

    def test_trap_poppk_overrides_endpoint(self, load_fixture_with_meta):
        """AIC-POPPK 선언 + 모순 endpoint(PK_CONCENTRATION, 단독이면 fallback AIC-PK) → 선언 우선.
        A0는 df 미참조(meta-only); 경합 신호는 endpoint_data_type fallback(유일 경합 경로)."""
        df, meta, expected = load_fixture_with_meta("c0200", "trap_poppk_overrides_endpoint")
        result = verify_a0_analysis_intent(df, meta)
        assert result["a0_state"] == expected["a0_state"]
        assert result["a0_state"] == "AIC-POPPK"
        assert result["pass"] == expected["pass"]
        assert result["route_to_q"] == expected["route_to_q"]

    def test_trap_er_declared_overrides_endpoint(self, load_fixture_with_meta):
        """AIC-ER 선언 + endpoint=PK_CONCENTRATION(scope 내, 단독이면 fallback AIC-PK) → 선언 우선 AIC-ER."""
        df, meta, expected = load_fixture_with_meta("c0200", "trap_er_declared_overrides_endpoint")
        result = verify_a0_analysis_intent(df, meta)
        assert result["a0_state"] == expected["a0_state"]
        assert result["a0_state"] == "AIC-ER"
        assert result["pass"] == expected["pass"]
        assert result["route_to_q"] == expected["route_to_q"]

    def test_trap_ddi_overrides_endpoint(self, load_fixture_with_meta):
        """AIC-DDI 선언 + 모순 endpoint(PK_CONCENTRATION, 단독이면 AIC-PK) → 선언 우선 AIC-DDI."""
        df, meta, expected = load_fixture_with_meta("c0200", "trap_ddi_overrides_endpoint")
        result = verify_a0_analysis_intent(df, meta)
        assert result["a0_state"] == expected["a0_state"]
        assert result["a0_state"] == "AIC-DDI"
        assert result["pass"] == expected["pass"]
        assert result["route_to_q"] == expected["route_to_q"]

    def test_trap_peds_overrides_endpoint(self, load_fixture_with_meta):
        """AIC-PEDS 선언 + 모순 endpoint(PK_CONCENTRATION, 단독이면 AIC-PK) → 선언 우선 AIC-PEDS."""
        df, meta, expected = load_fixture_with_meta("c0200", "trap_peds_overrides_endpoint")
        result = verify_a0_analysis_intent(df, meta)
        assert result["a0_state"] == expected["a0_state"]
        assert result["a0_state"] == "AIC-PEDS"
        assert result["pass"] == expected["pass"]
        assert result["route_to_q"] == expected["route_to_q"]

    def test_trap_special_overrides_endpoint(self, load_fixture_with_meta):
        """AIC-SPECIAL 선언 + 모순 endpoint(PK_CONCENTRATION, 단독이면 AIC-PK) → 선언 우선 AIC-SPECIAL."""
        df, meta, expected = load_fixture_with_meta("c0200", "trap_special_overrides_endpoint")
        result = verify_a0_analysis_intent(df, meta)
        assert result["a0_state"] == expected["a0_state"]
        assert result["a0_state"] == "AIC-SPECIAL"
        assert result["pass"] == expected["pass"]
        assert result["route_to_q"] == expected["route_to_q"]

    def test_trap_custom_overrides_endpoint(self, load_fixture_with_meta):
        """AIC-CUSTOM 선언(+policy_document) + 모순 endpoint(PK_CONCENTRATION, 단독이면 AIC-PK) → 선언 우선 AIC-CUSTOM."""
        df, meta, expected = load_fixture_with_meta("c0200", "trap_custom_overrides_endpoint")
        result = verify_a0_analysis_intent(df, meta)
        assert result["a0_state"] == expected["a0_state"]
        assert result["a0_state"] == "AIC-CUSTOM"
        assert result["pass"] == expected["pass"]
        assert result["route_to_q"] == expected["route_to_q"]


class TestC0204:
    """c0204 — A4 투여 완결성 평가 (VERIFY AMT)

    postcondition_predicate:
        meta.get('a4_state') in ['COMPLETE','WEIGHT-BASED','BSA-BASED','PLANNED-FALLBACK','ADDL-II','ADDL-ACTUAL-CONFLICT','TITRATION-ADAPTIVE','LOADING-MAINTENANCE','INFUSION-STOP-RESTART','PARTIAL-RECOVERY','COMBINATION','MISSING-NO-POLICY','UNRECOVERABLE']

    srp_intent: VERIFY AMT
    kind: verify
    can_route_to_q: [Q08, Q14]   (route_to_q ∈ {None, Q08, Q14}; Q04/INVALID 종착은 하류 ROUTE c — provenance_gaps GAP-5)
    verify_visualization:
        pass_route_to: c0205
        fail_route_to: Q08
    """

    # --- 13 happy (one per a4_state) ---

    def test_happy_complete(self, load_fixture_with_meta):
        """dose 행 존재, 결함 없음 → COMPLETE, pass(→c0205)."""
        df, meta, expected = load_fixture_with_meta("c0204", "happy_complete")
        result = verify_amt(df, meta)
        assert result["a4_state"] == expected["a4_state"]
        assert result["pass"] == expected["pass"]
        assert result["route_to_q"] == expected["route_to_q"]
        assert meta.get('a4_state') in ['COMPLETE','WEIGHT-BASED','BSA-BASED','PLANNED-FALLBACK','ADDL-II','ADDL-ACTUAL-CONFLICT','TITRATION-ADAPTIVE','LOADING-MAINTENANCE','INFUSION-STOP-RESTART','PARTIAL-RECOVERY','COMBINATION','MISSING-NO-POLICY','UNRECOVERABLE']

    def test_happy_weight_based(self, load_fixture_with_meta):
        """체중 기반 용량 → WEIGHT-BASED."""
        df, meta, expected = load_fixture_with_meta("c0204", "happy_weight_based")
        result = verify_amt(df, meta)
        assert result["a4_state"] == expected["a4_state"]
        assert result["pass"] == expected["pass"]
        assert meta.get('a4_state') in ['COMPLETE','WEIGHT-BASED','BSA-BASED','PLANNED-FALLBACK','ADDL-II','ADDL-ACTUAL-CONFLICT','TITRATION-ADAPTIVE','LOADING-MAINTENANCE','INFUSION-STOP-RESTART','PARTIAL-RECOVERY','COMBINATION','MISSING-NO-POLICY','UNRECOVERABLE']

    def test_happy_bsa_based(self, load_fixture_with_meta):
        """BSA 기반 용량 → BSA-BASED."""
        df, meta, expected = load_fixture_with_meta("c0204", "happy_bsa_based")
        result = verify_amt(df, meta)
        assert result["a4_state"] == expected["a4_state"]
        assert result["pass"] == expected["pass"]
        assert meta.get('a4_state') in ['COMPLETE','WEIGHT-BASED','BSA-BASED','PLANNED-FALLBACK','ADDL-II','ADDL-ACTUAL-CONFLICT','TITRATION-ADAPTIVE','LOADING-MAINTENANCE','INFUSION-STOP-RESTART','PARTIAL-RECOVERY','COMBINATION','MISSING-NO-POLICY','UNRECOVERABLE']

    def test_happy_planned_fallback(self, load_fixture_with_meta):
        """actual 부재, planned 사용 → PLANNED-FALLBACK."""
        df, meta, expected = load_fixture_with_meta("c0204", "happy_planned_fallback")
        result = verify_amt(df, meta)
        assert result["a4_state"] == expected["a4_state"]
        assert result["pass"] == expected["pass"]
        assert meta.get('a4_state') in ['COMPLETE','WEIGHT-BASED','BSA-BASED','PLANNED-FALLBACK','ADDL-II','ADDL-ACTUAL-CONFLICT','TITRATION-ADAPTIVE','LOADING-MAINTENANCE','INFUSION-STOP-RESTART','PARTIAL-RECOVERY','COMBINATION','MISSING-NO-POLICY','UNRECOVERABLE']

    def test_happy_addl_ii(self, load_fixture_with_meta):
        """고정용량 반복 → ADDL-II."""
        df, meta, expected = load_fixture_with_meta("c0204", "happy_addl_ii")
        result = verify_amt(df, meta)
        assert result["a4_state"] == expected["a4_state"]
        assert result["pass"] == expected["pass"]
        assert meta.get('a4_state') in ['COMPLETE','WEIGHT-BASED','BSA-BASED','PLANNED-FALLBACK','ADDL-II','ADDL-ACTUAL-CONFLICT','TITRATION-ADAPTIVE','LOADING-MAINTENANCE','INFUSION-STOP-RESTART','PARTIAL-RECOVERY','COMBINATION','MISSING-NO-POLICY','UNRECOVERABLE']

    def test_happy_addl_actual_conflict(self, load_fixture_with_meta):
        """implied ADDL+II vs actual 충돌 → ADDL-ACTUAL-CONFLICT, Q14."""
        df, meta, expected = load_fixture_with_meta("c0204", "happy_addl_actual_conflict")
        result = verify_amt(df, meta)
        assert result["a4_state"] == expected["a4_state"]
        assert result["pass"] == expected["pass"]
        assert result["route_to_q"] == "Q14"
        assert meta.get('a4_state') in ['COMPLETE','WEIGHT-BASED','BSA-BASED','PLANNED-FALLBACK','ADDL-II','ADDL-ACTUAL-CONFLICT','TITRATION-ADAPTIVE','LOADING-MAINTENANCE','INFUSION-STOP-RESTART','PARTIAL-RECOVERY','COMBINATION','MISSING-NO-POLICY','UNRECOVERABLE']

    def test_happy_titration_adaptive(self, load_fixture_with_meta):
        """가변용량 + 정책 존재 → TITRATION-ADAPTIVE, pass(REPAIR)."""
        df, meta, expected = load_fixture_with_meta("c0204", "happy_titration_adaptive")
        result = verify_amt(df, meta)
        assert result["a4_state"] == expected["a4_state"]
        assert result["pass"] == expected["pass"]
        assert result["route_to_q"] is None
        assert meta.get('a4_state') in ['COMPLETE','WEIGHT-BASED','BSA-BASED','PLANNED-FALLBACK','ADDL-II','ADDL-ACTUAL-CONFLICT','TITRATION-ADAPTIVE','LOADING-MAINTENANCE','INFUSION-STOP-RESTART','PARTIAL-RECOVERY','COMBINATION','MISSING-NO-POLICY','UNRECOVERABLE']

    def test_happy_loading_maintenance(self, load_fixture_with_meta):
        """loading+maintenance + 정책 존재 → LOADING-MAINTENANCE, pass."""
        df, meta, expected = load_fixture_with_meta("c0204", "happy_loading_maintenance")
        result = verify_amt(df, meta)
        assert result["a4_state"] == expected["a4_state"]
        assert result["pass"] == expected["pass"]
        assert meta.get('a4_state') in ['COMPLETE','WEIGHT-BASED','BSA-BASED','PLANNED-FALLBACK','ADDL-II','ADDL-ACTUAL-CONFLICT','TITRATION-ADAPTIVE','LOADING-MAINTENANCE','INFUSION-STOP-RESTART','PARTIAL-RECOVERY','COMBINATION','MISSING-NO-POLICY','UNRECOVERABLE']

    def test_happy_infusion_stop_restart(self, load_fixture_with_meta):
        """주입 중단/재개 → INFUSION-STOP-RESTART (c0204 scope 내 route_to_q=None)."""
        df, meta, expected = load_fixture_with_meta("c0204", "happy_infusion_stop_restart")
        result = verify_amt(df, meta)
        assert result["a4_state"] == expected["a4_state"]
        assert result["route_to_q"] is None
        assert meta.get('a4_state') in ['COMPLETE','WEIGHT-BASED','BSA-BASED','PLANNED-FALLBACK','ADDL-II','ADDL-ACTUAL-CONFLICT','TITRATION-ADAPTIVE','LOADING-MAINTENANCE','INFUSION-STOP-RESTART','PARTIAL-RECOVERY','COMBINATION','MISSING-NO-POLICY','UNRECOVERABLE']

    def test_happy_partial_recovery(self, load_fixture_with_meta):
        """일부 dose 복원 + flag → PARTIAL-RECOVERY."""
        df, meta, expected = load_fixture_with_meta("c0204", "happy_partial_recovery")
        result = verify_amt(df, meta)
        assert result["a4_state"] == expected["a4_state"]
        assert result["pass"] == expected["pass"]
        assert meta.get('a4_state') in ['COMPLETE','WEIGHT-BASED','BSA-BASED','PLANNED-FALLBACK','ADDL-II','ADDL-ACTUAL-CONFLICT','TITRATION-ADAPTIVE','LOADING-MAINTENANCE','INFUSION-STOP-RESTART','PARTIAL-RECOVERY','COMBINATION','MISSING-NO-POLICY','UNRECOVERABLE']

    def test_happy_combination(self, load_fixture_with_meta):
        """병용 regimen → COMBINATION."""
        df, meta, expected = load_fixture_with_meta("c0204", "happy_combination")
        result = verify_amt(df, meta)
        assert result["a4_state"] == expected["a4_state"]
        assert result["pass"] == expected["pass"]
        assert meta.get('a4_state') in ['COMPLETE','WEIGHT-BASED','BSA-BASED','PLANNED-FALLBACK','ADDL-II','ADDL-ACTUAL-CONFLICT','TITRATION-ADAPTIVE','LOADING-MAINTENANCE','INFUSION-STOP-RESTART','PARTIAL-RECOVERY','COMBINATION','MISSING-NO-POLICY','UNRECOVERABLE']

    def test_happy_missing_no_policy(self, load_fixture_with_meta):
        """dose 누락 + 복원정책 없음 → MISSING-NO-POLICY, Q08."""
        df, meta, expected = load_fixture_with_meta("c0204", "happy_missing_no_policy")
        result = verify_amt(df, meta)
        assert result["a4_state"] == expected["a4_state"]
        assert result["pass"] == expected["pass"]
        assert result["route_to_q"] == "Q08"
        assert meta.get('a4_state') in ['COMPLETE','WEIGHT-BASED','BSA-BASED','PLANNED-FALLBACK','ADDL-II','ADDL-ACTUAL-CONFLICT','TITRATION-ADAPTIVE','LOADING-MAINTENANCE','INFUSION-STOP-RESTART','PARTIAL-RECOVERY','COMBINATION','MISSING-NO-POLICY','UNRECOVERABLE']

    def test_happy_unrecoverable(self, load_fixture_with_meta):
        """dose 복원 불가 → UNRECOVERABLE (c0204 scope 내 route_to_q=None)."""
        df, meta, expected = load_fixture_with_meta("c0204", "happy_unrecoverable")
        result = verify_amt(df, meta)
        assert result["a4_state"] == expected["a4_state"]
        assert result["route_to_q"] is None
        assert meta.get('a4_state') in ['COMPLETE','WEIGHT-BASED','BSA-BASED','PLANNED-FALLBACK','ADDL-II','ADDL-ACTUAL-CONFLICT','TITRATION-ADAPTIVE','LOADING-MAINTENANCE','INFUSION-STOP-RESTART','PARTIAL-RECOVERY','COMBINATION','MISSING-NO-POLICY','UNRECOVERABLE']

    # --- edge ---

    def test_edge_minimal(self, load_fixture_with_meta):
        """최소 dose 1행 → COMPLETE (기본 경로)."""
        df, meta, expected = load_fixture_with_meta("c0204", "edge_minimal")
        result = verify_amt(df, meta)
        assert result["a4_state"] == expected["a4_state"]
        assert result["pass"] == expected["pass"]
        assert meta.get('a4_state') in ['COMPLETE','WEIGHT-BASED','BSA-BASED','PLANNED-FALLBACK','ADDL-II','ADDL-ACTUAL-CONFLICT','TITRATION-ADAPTIVE','LOADING-MAINTENANCE','INFUSION-STOP-RESTART','PARTIAL-RECOVERY','COMBINATION','MISSING-NO-POLICY','UNRECOVERABLE']

    # --- category / routing traps ---

    def test_trap_q08_routing(self, load_fixture_with_meta):
        """MISSING-NO-POLICY → Q08 (명시 routing assert)."""
        df, meta, expected = load_fixture_with_meta("c0204", "trap_q08_routing")
        result = verify_amt(df, meta)
        assert result["a4_state"] == "MISSING-NO-POLICY"
        assert result["pass"] is False
        assert result["route_to_q"] == "Q08"

    def test_trap_q14_routing(self, load_fixture_with_meta):
        """ADDL-ACTUAL-CONFLICT → Q14 (명시 routing assert)."""
        df, meta, expected = load_fixture_with_meta("c0204", "trap_q14_routing")
        result = verify_amt(df, meta)
        assert result["a4_state"] == "ADDL-ACTUAL-CONFLICT"
        assert result["pass"] is False
        assert result["route_to_q"] == "Q14"

    def test_trap_addl_ii_vs_titration(self, load_fixture_with_meta):
        """반복 dose처럼 보이나 가변용량 titration → TITRATION-ADAPTIVE (ADDL-II 아님)."""
        df, meta, expected = load_fixture_with_meta("c0204", "trap_addl_ii_vs_titration")
        result = verify_amt(df, meta)
        assert result["a4_state"] == expected["a4_state"]
        assert result["a4_state"] == "TITRATION-ADAPTIVE"

    def test_trap_conflict_priority(self, load_fixture_with_meta):
        """충돌 + addl-ii 혼재 → ADDL-ACTUAL-CONFLICT 우선(universe_sm 136), Q14."""
        df, meta, expected = load_fixture_with_meta("c0204", "trap_conflict_priority")
        result = verify_amt(df, meta)
        assert result["a4_state"] == "ADDL-ACTUAL-CONFLICT"
        assert result["route_to_q"] == "Q14"

    def test_trap_titration_no_policy_q08(self, load_fixture_with_meta):
        """TITRATION-ADAPTIVE + 정책 부재 → 상태 유지, route Q08."""
        df, meta, expected = load_fixture_with_meta("c0204", "trap_titration_no_policy_q08")
        result = verify_amt(df, meta)
        assert result["a4_state"] == "TITRATION-ADAPTIVE"
        assert result["pass"] is False
        assert result["route_to_q"] == "Q08"

    def test_trap_loading_no_policy_q08(self, load_fixture_with_meta):
        """LOADING-MAINTENANCE + 정책 부재 → 상태 유지, route Q08."""
        df, meta, expected = load_fixture_with_meta("c0204", "trap_loading_no_policy_q08")
        result = verify_amt(df, meta)
        assert result["a4_state"] == "LOADING-MAINTENANCE"
        assert result["route_to_q"] == "Q08"

    def test_trap_infusion_no_q(self, load_fixture_with_meta):
        """INFUSION-STOP-RESTART는 분류하되 Q04 날조 금지 → route_to_q=None."""
        df, meta, expected = load_fixture_with_meta("c0204", "trap_infusion_no_q")
        result = verify_amt(df, meta)
        assert result["a4_state"] == "INFUSION-STOP-RESTART"
        assert result["route_to_q"] is None
        assert result["pass"] is True

    def test_trap_unrecoverable_no_q(self, load_fixture_with_meta):
        """UNRECOVERABLE은 분류하되 INVALID/Q 날조 금지 → route_to_q=None."""
        df, meta, expected = load_fixture_with_meta("c0204", "trap_unrecoverable_no_q")
        result = verify_amt(df, meta)
        assert result["a4_state"] == "UNRECOVERABLE"
        assert result["route_to_q"] is None

    def test_trap_no_doses_not_complete(self, load_fixture_with_meta):
        """dose 행 부재인데 COMPLETE로 silent 통과 금지 → MISSING-NO-POLICY, Q08."""
        df, meta, expected = load_fixture_with_meta("c0204", "trap_no_doses_not_complete")
        result = verify_amt(df, meta)
        assert result["a4_state"] == "MISSING-NO-POLICY"
        assert result["route_to_q"] == "Q08"

    # --- 선언이 df no-dose(→MISSING-NO-POLICY) 신호를 이김 (AUDIT #2: 선언-직결 regimen override trap) ---

    def test_trap_weight_based_overrides_no_dose(self, load_fixture_with_meta):
        """dose 행 부재(단독이면 MISSING-NO-POLICY/Q08)인데 dose_regimen=weight-based 선언 → 선언 우선."""
        df, meta, expected = load_fixture_with_meta("c0204", "trap_weight_based_overrides_no_dose")
        result = verify_amt(df, meta)
        assert result["a4_state"] == expected["a4_state"]
        assert result["a4_state"] == "WEIGHT-BASED"
        assert result["pass"] is True
        assert result["route_to_q"] is None

    def test_trap_bsa_based_overrides_no_dose(self, load_fixture_with_meta):
        """dose 행 부재(단독이면 MISSING-NO-POLICY/Q08)인데 dose_regimen=bsa-based 선언 → 선언 우선."""
        df, meta, expected = load_fixture_with_meta("c0204", "trap_bsa_based_overrides_no_dose")
        result = verify_amt(df, meta)
        assert result["a4_state"] == expected["a4_state"]
        assert result["a4_state"] == "BSA-BASED"
        assert result["pass"] is True
        assert result["route_to_q"] is None

    def test_trap_planned_fallback_overrides_no_dose(self, load_fixture_with_meta):
        """dose 행 부재(단독이면 MISSING-NO-POLICY/Q08)인데 dose_regimen=planned-fallback 선언 → 선언 우선."""
        df, meta, expected = load_fixture_with_meta("c0204", "trap_planned_fallback_overrides_no_dose")
        result = verify_amt(df, meta)
        assert result["a4_state"] == expected["a4_state"]
        assert result["a4_state"] == "PLANNED-FALLBACK"
        assert result["pass"] is True
        assert result["route_to_q"] is None

    def test_trap_addl_ii_overrides_no_dose(self, load_fixture_with_meta):
        """dose 행 부재(단독이면 MISSING-NO-POLICY/Q08)인데 dose_regimen=addl-ii 선언 → 선언 우선."""
        df, meta, expected = load_fixture_with_meta("c0204", "trap_addl_ii_overrides_no_dose")
        result = verify_amt(df, meta)
        assert result["a4_state"] == expected["a4_state"]
        assert result["a4_state"] == "ADDL-II"
        assert result["pass"] is True
        assert result["route_to_q"] is None

    def test_trap_partial_recovery_overrides_no_dose(self, load_fixture_with_meta):
        """dose 행 부재(단독이면 MISSING-NO-POLICY/Q08)인데 dose_regimen=partial-recovery 선언 → 선언 우선."""
        df, meta, expected = load_fixture_with_meta("c0204", "trap_partial_recovery_overrides_no_dose")
        result = verify_amt(df, meta)
        assert result["a4_state"] == expected["a4_state"]
        assert result["a4_state"] == "PARTIAL-RECOVERY"
        assert result["pass"] is True
        assert result["route_to_q"] is None

    def test_trap_combination_overrides_no_dose(self, load_fixture_with_meta):
        """dose 행 부재(단독이면 MISSING-NO-POLICY/Q08)인데 dose_regimen=combination 선언 → 선언 우선."""
        df, meta, expected = load_fixture_with_meta("c0204", "trap_combination_overrides_no_dose")
        result = verify_amt(df, meta)
        assert result["a4_state"] == expected["a4_state"]
        assert result["a4_state"] == "COMBINATION"
        assert result["pass"] is True
        assert result["route_to_q"] is None


class TestC0201:
    """c0201 — A1 연구 통합 수준 평가 (DETECT SHEET_INVENTORY BY ACROSS_FILE)

    postcondition_predicate:
        meta.get('a1_state') in ['SINGLE','MULTI-HOMO','MULTI-HETERO','MULTI-SITE','INTERIM']

    srp_intent: DETECT SHEET_INVENTORY BY ACROSS_FILE
    kind: detect
    can_route_to_q: [Q05]   (route_to_q ∈ {None, Q05}; Q05 trigger: A1∈{MULTI-HOMO,MULTI-HETERO,MULTI-SITE} AND harmonization policy 부재)
    verify_visualization:
        pass_route_to: c0202
        fail_route_to: Q05
    """

    # --- 5 happy (one per a1_state) ---

    def test_happy_single(self, load_fixture_with_meta):
        """단일 연구 → SINGLE, pass(→c0202)."""
        df, meta, expected = load_fixture_with_meta("c0201", "happy_single")
        result = detect_sheet_inventory(df, meta)
        assert result["a1_state"] == expected["a1_state"]
        assert result["pass"] == expected["pass"]
        assert result["route_to_q"] == expected["route_to_q"]
        assert meta.get('a1_state') in ['SINGLE','MULTI-HOMO','MULTI-HETERO','MULTI-SITE','INTERIM']

    def test_happy_multi_homo(self, load_fixture_with_meta):
        """동질 복수 연구 + harmonization 정책 존재 → MULTI-HOMO, pass."""
        df, meta, expected = load_fixture_with_meta("c0201", "happy_multi_homo")
        result = detect_sheet_inventory(df, meta)
        assert result["a1_state"] == expected["a1_state"]
        assert result["pass"] == expected["pass"]
        assert result["route_to_q"] == expected["route_to_q"]
        assert meta.get('a1_state') in ['SINGLE','MULTI-HOMO','MULTI-HETERO','MULTI-SITE','INTERIM']

    def test_happy_multi_hetero(self, load_fixture_with_meta):
        """이질 복수 연구 + 정책 존재 → MULTI-HETERO, pass."""
        df, meta, expected = load_fixture_with_meta("c0201", "happy_multi_hetero")
        result = detect_sheet_inventory(df, meta)
        assert result["a1_state"] == expected["a1_state"]
        assert result["pass"] == expected["pass"]
        assert result["route_to_q"] == expected["route_to_q"]
        assert meta.get('a1_state') in ['SINGLE','MULTI-HOMO','MULTI-HETERO','MULTI-SITE','INTERIM']

    def test_happy_multi_site(self, load_fixture_with_meta):
        """multi-site 연구 + 정책 존재 → MULTI-SITE, pass."""
        df, meta, expected = load_fixture_with_meta("c0201", "happy_multi_site")
        result = detect_sheet_inventory(df, meta)
        assert result["a1_state"] == expected["a1_state"]
        assert result["pass"] == expected["pass"]
        assert result["route_to_q"] == expected["route_to_q"]
        assert meta.get('a1_state') in ['SINGLE','MULTI-HOMO','MULTI-HETERO','MULTI-SITE','INTERIM']

    def test_happy_interim(self, load_fixture_with_meta):
        """중간 분석 cut → INTERIM, pass."""
        df, meta, expected = load_fixture_with_meta("c0201", "happy_interim")
        result = detect_sheet_inventory(df, meta)
        assert result["a1_state"] == expected["a1_state"]
        assert result["pass"] == expected["pass"]
        assert result["route_to_q"] == expected["route_to_q"]
        assert meta.get('a1_state') in ['SINGLE','MULTI-HOMO','MULTI-HETERO','MULTI-SITE','INTERIM']

    # --- edge ---

    def test_edge_single_study_df_fallback(self, load_fixture_with_meta):
        """descriptor 부재, df study_id 단일 → SINGLE (df 추론)."""
        df, meta, expected = load_fixture_with_meta("c0201", "edge_single_study_df_fallback")
        result = detect_sheet_inventory(df, meta)
        assert result["a1_state"] == expected["a1_state"]
        assert result["pass"] == expected["pass"]
        assert meta.get('a1_state') in ['SINGLE','MULTI-HOMO','MULTI-HETERO','MULTI-SITE','INTERIM']

    # --- 5 category traps (one per a1_state) ---

    def test_trap_single_many_subjects(self, load_fixture_with_meta):
        """행·subject 다수지만 study 1개 → SINGLE (다수 행에 속지 않음)."""
        df, meta, expected = load_fixture_with_meta("c0201", "trap_single_many_subjects")
        result = detect_sheet_inventory(df, meta)
        assert result["a1_state"] == "SINGLE"

    def test_trap_multi_homo_looks_single(self, load_fixture_with_meta):
        """df study_id 1개로 보이나 선언이 multi-homo → 선언 우선 MULTI-HOMO."""
        df, meta, expected = load_fixture_with_meta("c0201", "trap_multi_homo_looks_single")
        result = detect_sheet_inventory(df, meta)
        assert result["a1_state"] == "MULTI-HOMO"

    def test_trap_multi_hetero_vs_homo(self, load_fixture_with_meta):
        """multi-hetero 선언이 homo로 silent 격하되면 안 됨 → MULTI-HETERO."""
        df, meta, expected = load_fixture_with_meta("c0201", "trap_multi_hetero_vs_homo")
        result = detect_sheet_inventory(df, meta)
        assert result["a1_state"] == "MULTI-HETERO"

    def test_trap_multi_site_vs_hetero(self, load_fixture_with_meta):
        """multi-site 선언이 hetero로 silent 혼동되면 안 됨 → MULTI-SITE."""
        df, meta, expected = load_fixture_with_meta("c0201", "trap_multi_site_vs_hetero")
        result = detect_sheet_inventory(df, meta)
        assert result["a1_state"] == "MULTI-SITE"

    def test_trap_interim_vs_single(self, load_fixture_with_meta):
        """interim cut이 study 1개라 SINGLE로 silent 통과되면 안 됨 → INTERIM."""
        df, meta, expected = load_fixture_with_meta("c0201", "trap_interim_vs_single")
        result = detect_sheet_inventory(df, meta)
        assert result["a1_state"] == "INTERIM"

    # --- routing trap ---

    def test_trap_q05_routing(self, load_fixture_with_meta):
        """MULTI-* + harmonization 정책 부재 → Q05 (명시 routing assert)."""
        df, meta, expected = load_fixture_with_meta("c0201", "trap_q05_routing")
        result = detect_sheet_inventory(df, meta)
        assert result["a1_state"] in ["MULTI-HOMO", "MULTI-HETERO", "MULTI-SITE"]
        assert result["pass"] is False
        assert result["route_to_q"] == "Q05"


class TestC0202:
    """c0202 — A2 연구 설계 분류 (CLASSIFY REGIMEN_DESCRIPTOR)

    postcondition_predicate:
        meta.get('a2_state') in ['PARALLEL','SAD-MAD','CROSSOVER','BE','DDI','FOOD-EFFECT','SPECIAL-POP','PEDIATRIC','TDM-RWD','PRECLINICAL']

    srp_intent: CLASSIFY REGIMEN_DESCRIPTOR
    kind: detect
    can_route_to_q: []   (순수 분류기 — route_to_q 항상 None, pass 항상 True; universe_sm §3 A2는 Q/INVALID 라우팅 없음)
    verify_visualization:
        pass_route_to: c0203
        fail_route_to: None
    """

    # --- 10 happy (one per a2_state) ---

    def test_happy_parallel(self, load_fixture_with_meta):
        """평행군 설계 → PARALLEL, pass(→c0203)."""
        df, meta, expected = load_fixture_with_meta("c0202", "happy_parallel")
        result = classify_regimen_descriptor(df, meta)
        assert result["a2_state"] == expected["a2_state"]
        assert result["pass"] == expected["pass"]
        assert result["route_to_q"] == expected["route_to_q"]
        assert meta.get('a2_state') in ['PARALLEL','SAD-MAD','CROSSOVER','BE','DDI','FOOD-EFFECT','SPECIAL-POP','PEDIATRIC','TDM-RWD','PRECLINICAL']

    def test_happy_sad_mad(self, load_fixture_with_meta):
        """단회/다회 용량증량(SAD/MAD) → SAD-MAD, pass."""
        df, meta, expected = load_fixture_with_meta("c0202", "happy_sad_mad")
        result = classify_regimen_descriptor(df, meta)
        assert result["a2_state"] == expected["a2_state"]
        assert result["pass"] == expected["pass"]
        assert result["route_to_q"] == expected["route_to_q"]
        assert meta.get('a2_state') in ['PARALLEL','SAD-MAD','CROSSOVER','BE','DDI','FOOD-EFFECT','SPECIAL-POP','PEDIATRIC','TDM-RWD','PRECLINICAL']

    def test_happy_crossover(self, load_fixture_with_meta):
        """교차 설계 → CROSSOVER, pass."""
        df, meta, expected = load_fixture_with_meta("c0202", "happy_crossover")
        result = classify_regimen_descriptor(df, meta)
        assert result["a2_state"] == expected["a2_state"]
        assert result["pass"] == expected["pass"]
        assert result["route_to_q"] == expected["route_to_q"]
        assert meta.get('a2_state') in ['PARALLEL','SAD-MAD','CROSSOVER','BE','DDI','FOOD-EFFECT','SPECIAL-POP','PEDIATRIC','TDM-RWD','PRECLINICAL']

    def test_happy_be(self, load_fixture_with_meta):
        """생물학적 동등성 → BE, pass."""
        df, meta, expected = load_fixture_with_meta("c0202", "happy_be")
        result = classify_regimen_descriptor(df, meta)
        assert result["a2_state"] == expected["a2_state"]
        assert result["pass"] == expected["pass"]
        assert result["route_to_q"] == expected["route_to_q"]
        assert meta.get('a2_state') in ['PARALLEL','SAD-MAD','CROSSOVER','BE','DDI','FOOD-EFFECT','SPECIAL-POP','PEDIATRIC','TDM-RWD','PRECLINICAL']

    def test_happy_ddi(self, load_fixture_with_meta):
        """약물상호작용 → DDI, pass."""
        df, meta, expected = load_fixture_with_meta("c0202", "happy_ddi")
        result = classify_regimen_descriptor(df, meta)
        assert result["a2_state"] == expected["a2_state"]
        assert result["pass"] == expected["pass"]
        assert result["route_to_q"] == expected["route_to_q"]
        assert meta.get('a2_state') in ['PARALLEL','SAD-MAD','CROSSOVER','BE','DDI','FOOD-EFFECT','SPECIAL-POP','PEDIATRIC','TDM-RWD','PRECLINICAL']

    def test_happy_food_effect(self, load_fixture_with_meta):
        """음식 영향 → FOOD-EFFECT, pass."""
        df, meta, expected = load_fixture_with_meta("c0202", "happy_food_effect")
        result = classify_regimen_descriptor(df, meta)
        assert result["a2_state"] == expected["a2_state"]
        assert result["pass"] == expected["pass"]
        assert result["route_to_q"] == expected["route_to_q"]
        assert meta.get('a2_state') in ['PARALLEL','SAD-MAD','CROSSOVER','BE','DDI','FOOD-EFFECT','SPECIAL-POP','PEDIATRIC','TDM-RWD','PRECLINICAL']

    def test_happy_special_pop(self, load_fixture_with_meta):
        """특수 집단 → SPECIAL-POP, pass."""
        df, meta, expected = load_fixture_with_meta("c0202", "happy_special_pop")
        result = classify_regimen_descriptor(df, meta)
        assert result["a2_state"] == expected["a2_state"]
        assert result["pass"] == expected["pass"]
        assert result["route_to_q"] == expected["route_to_q"]
        assert meta.get('a2_state') in ['PARALLEL','SAD-MAD','CROSSOVER','BE','DDI','FOOD-EFFECT','SPECIAL-POP','PEDIATRIC','TDM-RWD','PRECLINICAL']

    def test_happy_pediatric(self, load_fixture_with_meta):
        """소아 연구 → PEDIATRIC, pass."""
        df, meta, expected = load_fixture_with_meta("c0202", "happy_pediatric")
        result = classify_regimen_descriptor(df, meta)
        assert result["a2_state"] == expected["a2_state"]
        assert result["pass"] == expected["pass"]
        assert result["route_to_q"] == expected["route_to_q"]
        assert meta.get('a2_state') in ['PARALLEL','SAD-MAD','CROSSOVER','BE','DDI','FOOD-EFFECT','SPECIAL-POP','PEDIATRIC','TDM-RWD','PRECLINICAL']

    def test_happy_tdm_rwd(self, load_fixture_with_meta):
        """TDM/실사용 데이터 → TDM-RWD, pass."""
        df, meta, expected = load_fixture_with_meta("c0202", "happy_tdm_rwd")
        result = classify_regimen_descriptor(df, meta)
        assert result["a2_state"] == expected["a2_state"]
        assert result["pass"] == expected["pass"]
        assert result["route_to_q"] == expected["route_to_q"]
        assert meta.get('a2_state') in ['PARALLEL','SAD-MAD','CROSSOVER','BE','DDI','FOOD-EFFECT','SPECIAL-POP','PEDIATRIC','TDM-RWD','PRECLINICAL']

    def test_happy_preclinical(self, load_fixture_with_meta):
        """전임상 → PRECLINICAL, pass."""
        df, meta, expected = load_fixture_with_meta("c0202", "happy_preclinical")
        result = classify_regimen_descriptor(df, meta)
        assert result["a2_state"] == expected["a2_state"]
        assert result["pass"] == expected["pass"]
        assert result["route_to_q"] == expected["route_to_q"]
        assert meta.get('a2_state') in ['PARALLEL','SAD-MAD','CROSSOVER','BE','DDI','FOOD-EFFECT','SPECIAL-POP','PEDIATRIC','TDM-RWD','PRECLINICAL']

    # --- 2 edge (선언 부재 → df fallback) ---

    def test_edge_parallel_df_fallback(self, load_fixture_with_meta):
        """선언 부재 + 평이한 df → PARALLEL(기본값)."""
        df, meta, expected = load_fixture_with_meta("c0202", "edge_parallel_df_fallback")
        result = classify_regimen_descriptor(df, meta)
        assert result["a2_state"] == expected["a2_state"]
        assert result["pass"] == expected["pass"]
        assert meta.get('a2_state') in ['PARALLEL','SAD-MAD','CROSSOVER','BE','DDI','FOOD-EFFECT','SPECIAL-POP','PEDIATRIC','TDM-RWD','PRECLINICAL']

    def test_edge_crossover_df_fallback(self, load_fixture_with_meta):
        """선언 부재 + period/sequence 컬럼 → CROSSOVER(df 신호)."""
        df, meta, expected = load_fixture_with_meta("c0202", "edge_crossover_df_fallback")
        result = classify_regimen_descriptor(df, meta)
        assert result["a2_state"] == expected["a2_state"]
        assert result["pass"] == expected["pass"]
        assert meta.get('a2_state') in ['PARALLEL','SAD-MAD','CROSSOVER','BE','DDI','FOOD-EFFECT','SPECIAL-POP','PEDIATRIC','TDM-RWD','PRECLINICAL']

    # --- 10 category trap (state별 오분류 유발; 선언 우선 = 선언이 df 신호를 이김) ---

    def test_trap_parallel_vs_crossover(self, load_fixture_with_meta):
        """PARALLEL 선언이 period/seq df 때문에 CROSSOVER로 silent 격상되면 안 됨 → PARALLEL."""
        df, meta, expected = load_fixture_with_meta("c0202", "trap_parallel_vs_crossover")
        result = classify_regimen_descriptor(df, meta)
        assert result["a2_state"] == "PARALLEL"
        assert result["route_to_q"] is None

    def test_trap_sad_mad_vs_parallel(self, load_fixture_with_meta):
        """SAD-MAD 선언이 df 기본값 PARALLEL로 silent 격하되면 안 됨 → SAD-MAD."""
        df, meta, expected = load_fixture_with_meta("c0202", "trap_sad_mad_vs_parallel")
        result = classify_regimen_descriptor(df, meta)
        assert result["a2_state"] == "SAD-MAD"
        assert result["route_to_q"] is None

    def test_trap_crossover_vs_parallel(self, load_fixture_with_meta):
        """CROSSOVER 선언이 평이한 df 때문에 PARALLEL로 silent 격하되면 안 됨 → CROSSOVER."""
        df, meta, expected = load_fixture_with_meta("c0202", "trap_crossover_vs_parallel")
        result = classify_regimen_descriptor(df, meta)
        assert result["a2_state"] == "CROSSOVER"
        assert result["route_to_q"] is None

    def test_trap_be_vs_crossover(self, load_fixture_with_meta):
        """BE 선언이 period/seq df 때문에 CROSSOVER로 silent 혼동되면 안 됨 → BE."""
        df, meta, expected = load_fixture_with_meta("c0202", "trap_be_vs_crossover")
        result = classify_regimen_descriptor(df, meta)
        assert result["a2_state"] == "BE"
        assert result["route_to_q"] is None

    def test_trap_ddi_vs_parallel(self, load_fixture_with_meta):
        """DDI 선언이 df 기본값 PARALLEL로 silent 격하되면 안 됨 → DDI."""
        df, meta, expected = load_fixture_with_meta("c0202", "trap_ddi_vs_parallel")
        result = classify_regimen_descriptor(df, meta)
        assert result["a2_state"] == "DDI"
        assert result["route_to_q"] is None

    def test_trap_food_effect_vs_crossover(self, load_fixture_with_meta):
        """FOOD-EFFECT 선언이 period/seq df 때문에 CROSSOVER로 silent 혼동되면 안 됨 → FOOD-EFFECT."""
        df, meta, expected = load_fixture_with_meta("c0202", "trap_food_effect_vs_crossover")
        result = classify_regimen_descriptor(df, meta)
        assert result["a2_state"] == "FOOD-EFFECT"
        assert result["route_to_q"] is None

    def test_trap_special_pop_vs_parallel(self, load_fixture_with_meta):
        """SPECIAL-POP 선언이 df 기본값 PARALLEL로 silent 격하되면 안 됨 → SPECIAL-POP."""
        df, meta, expected = load_fixture_with_meta("c0202", "trap_special_pop_vs_parallel")
        result = classify_regimen_descriptor(df, meta)
        assert result["a2_state"] == "SPECIAL-POP"
        assert result["route_to_q"] is None

    def test_trap_pediatric_vs_special_pop(self, load_fixture_with_meta):
        """PEDIATRIC 선언이 상위 범주 SPECIAL-POP로 silent 격하되면 안 됨 → PEDIATRIC."""
        df, meta, expected = load_fixture_with_meta("c0202", "trap_pediatric_vs_special_pop")
        result = classify_regimen_descriptor(df, meta)
        assert result["a2_state"] == "PEDIATRIC"
        assert result["route_to_q"] is None

    def test_trap_tdm_rwd_vs_parallel(self, load_fixture_with_meta):
        """TDM-RWD 선언이 df 기본값 PARALLEL로 silent 격하되면 안 됨 → TDM-RWD."""
        df, meta, expected = load_fixture_with_meta("c0202", "trap_tdm_rwd_vs_parallel")
        result = classify_regimen_descriptor(df, meta)
        assert result["a2_state"] == "TDM-RWD"
        assert result["route_to_q"] is None

    def test_trap_preclinical_vs_parallel(self, load_fixture_with_meta):
        """PRECLINICAL 선언이 df 기본값 PARALLEL로 silent 격하되면 안 됨 → PRECLINICAL."""
        df, meta, expected = load_fixture_with_meta("c0202", "trap_preclinical_vs_parallel")
        result = classify_regimen_descriptor(df, meta)
        assert result["a2_state"] == "PRECLINICAL"
        assert result["route_to_q"] is None

    # --- spec consistency (순수 분류기 계약 고정; Q 라우팅 trap 없음) ---

    def test_spec_pure_classifier_contract(self):
        """c0202 spec: can_route_to_q=[], pass_route_to=c0203, fail_route_to=None."""
        import json
        from pathlib import Path
        spec_path = Path(__file__).resolve().parent.parent / "spec" / "c_units.json"
        with open(spec_path, encoding="utf-8") as f:
            units = json.load(f)
        entry = next(u for u in units if u["c_id"] == "c0202")
        assert entry["can_route_to_q"] == []
        assert entry["verify_visualization"]["pass_route_to"] == "c0203"
        assert entry["verify_visualization"]["fail_route_to"] is None


class TestC0203:
    """c0203 — A3 시간 유도 정책 평가 (DETECT TIME_FORMAT)

    postcondition_predicate:
        meta.get('a3_state') in ['ACTUAL','NOMINAL-ONLY','ACTUAL-PREFERRED','NOMINAL-PREFERRED','ELAPSED','INTERVAL','AMBIGUOUS','UNRECOVERABLE']

    srp_intent: DETECT TIME_FORMAT
    kind: detect
    can_route_to_q: [Q02, Q12]   (route_to_q ∈ {None, Q02, Q12}; Q02 trigger A3=AMBIGUOUS, Q12 trigger A3=UNRECOVERABLE)
    verify_visualization:
        pass_route_to: c0204
        fail_route_to: Q02
    """

    # --- 8 happy (one per a3_state) ---

    def test_happy_actual(self, load_fixture_with_meta):
        """실측 시간 → ACTUAL, pass(→c0204)."""
        df, meta, expected = load_fixture_with_meta("c0203", "happy_actual")
        result = detect_time_format(df, meta)
        assert result["a3_state"] == expected["a3_state"]
        assert result["pass"] == expected["pass"]
        assert result["route_to_q"] == expected["route_to_q"]
        assert meta.get('a3_state') in ['ACTUAL','NOMINAL-ONLY','ACTUAL-PREFERRED','NOMINAL-PREFERRED','ELAPSED','INTERVAL','AMBIGUOUS','UNRECOVERABLE']

    def test_happy_nominal_only(self, load_fixture_with_meta):
        """명목 시간만 존재 → NOMINAL-ONLY, pass."""
        df, meta, expected = load_fixture_with_meta("c0203", "happy_nominal_only")
        result = detect_time_format(df, meta)
        assert result["a3_state"] == expected["a3_state"]
        assert result["pass"] == expected["pass"]
        assert result["route_to_q"] == expected["route_to_q"]
        assert meta.get('a3_state') in ['ACTUAL','NOMINAL-ONLY','ACTUAL-PREFERRED','NOMINAL-PREFERRED','ELAPSED','INTERVAL','AMBIGUOUS','UNRECOVERABLE']

    def test_happy_actual_preferred(self, load_fixture_with_meta):
        """actual+nominal 공존, actual 우선 → ACTUAL-PREFERRED, pass."""
        df, meta, expected = load_fixture_with_meta("c0203", "happy_actual_preferred")
        result = detect_time_format(df, meta)
        assert result["a3_state"] == expected["a3_state"]
        assert result["pass"] == expected["pass"]
        assert result["route_to_q"] == expected["route_to_q"]
        assert meta.get('a3_state') in ['ACTUAL','NOMINAL-ONLY','ACTUAL-PREFERRED','NOMINAL-PREFERRED','ELAPSED','INTERVAL','AMBIGUOUS','UNRECOVERABLE']

    def test_happy_nominal_preferred(self, load_fixture_with_meta):
        """actual+nominal 공존, nominal 우선 → NOMINAL-PREFERRED, pass."""
        df, meta, expected = load_fixture_with_meta("c0203", "happy_nominal_preferred")
        result = detect_time_format(df, meta)
        assert result["a3_state"] == expected["a3_state"]
        assert result["pass"] == expected["pass"]
        assert result["route_to_q"] == expected["route_to_q"]
        assert meta.get('a3_state') in ['ACTUAL','NOMINAL-ONLY','ACTUAL-PREFERRED','NOMINAL-PREFERRED','ELAPSED','INTERVAL','AMBIGUOUS','UNRECOVERABLE']

    def test_happy_elapsed(self, load_fixture_with_meta):
        """경과 시간(anchor 기준) → ELAPSED, pass."""
        df, meta, expected = load_fixture_with_meta("c0203", "happy_elapsed")
        result = detect_time_format(df, meta)
        assert result["a3_state"] == expected["a3_state"]
        assert result["pass"] == expected["pass"]
        assert result["route_to_q"] == expected["route_to_q"]
        assert meta.get('a3_state') in ['ACTUAL','NOMINAL-ONLY','ACTUAL-PREFERRED','NOMINAL-PREFERRED','ELAPSED','INTERVAL','AMBIGUOUS','UNRECOVERABLE']

    def test_happy_interval(self, load_fixture_with_meta):
        """구간 시간(urine 등) → INTERVAL, pass."""
        df, meta, expected = load_fixture_with_meta("c0203", "happy_interval")
        result = detect_time_format(df, meta)
        assert result["a3_state"] == expected["a3_state"]
        assert result["pass"] == expected["pass"]
        assert result["route_to_q"] == expected["route_to_q"]
        assert meta.get('a3_state') in ['ACTUAL','NOMINAL-ONLY','ACTUAL-PREFERRED','NOMINAL-PREFERRED','ELAPSED','INTERVAL','AMBIGUOUS','UNRECOVERABLE']

    def test_happy_ambiguous(self, load_fixture_with_meta):
        """시간 정책 모호 → AMBIGUOUS, Q02."""
        df, meta, expected = load_fixture_with_meta("c0203", "happy_ambiguous")
        result = detect_time_format(df, meta)
        assert result["a3_state"] == expected["a3_state"]
        assert result["pass"] == expected["pass"]
        assert result["route_to_q"] == "Q02"
        assert meta.get('a3_state') in ['ACTUAL','NOMINAL-ONLY','ACTUAL-PREFERRED','NOMINAL-PREFERRED','ELAPSED','INTERVAL','AMBIGUOUS','UNRECOVERABLE']

    def test_happy_unrecoverable(self, load_fixture_with_meta):
        """시간 anchor 복원 불가 → UNRECOVERABLE, Q12 (INVALID 아님 — q_codes Q12)."""
        df, meta, expected = load_fixture_with_meta("c0203", "happy_unrecoverable")
        result = detect_time_format(df, meta)
        assert result["a3_state"] == expected["a3_state"]
        assert result["pass"] == expected["pass"]
        assert result["route_to_q"] == "Q12"
        assert meta.get('a3_state') in ['ACTUAL','NOMINAL-ONLY','ACTUAL-PREFERRED','NOMINAL-PREFERRED','ELAPSED','INTERVAL','AMBIGUOUS','UNRECOVERABLE']

    # --- edge ---

    def test_edge_time_uppercase(self, load_fixture_with_meta):
        """precondition의 TIME(대문자) 컬럼 분기 + df 추론 → ACTUAL."""
        df, meta, expected = load_fixture_with_meta("c0203", "edge_time_uppercase")
        result = detect_time_format(df, meta)
        assert result["a3_state"] == expected["a3_state"]
        assert result["pass"] == expected["pass"]
        assert meta.get('a3_state') in ['ACTUAL','NOMINAL-ONLY','ACTUAL-PREFERRED','NOMINAL-PREFERRED','ELAPSED','INTERVAL','AMBIGUOUS','UNRECOVERABLE']

    # --- 8 category traps (one per a3_state) ---

    def test_trap_actual_df_fallback(self, load_fixture_with_meta):
        """선언 부재, df 시간 전부 파싱가능 → ACTUAL (df 추론)."""
        df, meta, expected = load_fixture_with_meta("c0203", "trap_actual_df_fallback")
        result = detect_time_format(df, meta)
        assert result["a3_state"] == "ACTUAL"

    def test_trap_nominal_only_vs_actual(self, load_fixture_with_meta):
        """df 시간이 파싱가능(naive ACTUAL)이나 선언 nominal-only → NOMINAL-ONLY."""
        df, meta, expected = load_fixture_with_meta("c0203", "trap_nominal_only_vs_actual")
        result = detect_time_format(df, meta)
        assert result["a3_state"] == "NOMINAL-ONLY"

    def test_trap_actual_preferred_vs_actual(self, load_fixture_with_meta):
        """actual-preferred가 plain ACTUAL로 silent 격하되면 안 됨 → ACTUAL-PREFERRED."""
        df, meta, expected = load_fixture_with_meta("c0203", "trap_actual_preferred_vs_actual")
        result = detect_time_format(df, meta)
        assert result["a3_state"] == "ACTUAL-PREFERRED"

    def test_trap_nominal_preferred_vs_nominal_only(self, load_fixture_with_meta):
        """nominal-preferred가 NOMINAL-ONLY로 silent 혼동되면 안 됨 → NOMINAL-PREFERRED."""
        df, meta, expected = load_fixture_with_meta("c0203", "trap_nominal_preferred_vs_nominal_only")
        result = detect_time_format(df, meta)
        assert result["a3_state"] == "NOMINAL-PREFERRED"

    def test_trap_elapsed_vs_actual(self, load_fixture_with_meta):
        """elapsed 시간이 숫자라 ACTUAL로 silent 통과되면 안 됨 → ELAPSED."""
        df, meta, expected = load_fixture_with_meta("c0203", "trap_elapsed_vs_actual")
        result = detect_time_format(df, meta)
        assert result["a3_state"] == "ELAPSED"

    def test_trap_interval_vs_actual(self, load_fixture_with_meta):
        """구간 시간이 ACTUAL로 silent 통과되면 안 됨 → INTERVAL."""
        df, meta, expected = load_fixture_with_meta("c0203", "trap_interval_vs_actual")
        result = detect_time_format(df, meta)
        assert result["a3_state"] == "INTERVAL"

    def test_trap_ambiguous_mixed_tokens(self, load_fixture_with_meta):
        """혼재 토큰(숫자+텍스트)을 ACTUAL로 silent 통과 금지 → AMBIGUOUS."""
        df, meta, expected = load_fixture_with_meta("c0203", "trap_ambiguous_mixed_tokens")
        result = detect_time_format(df, meta)
        assert result["a3_state"] == "AMBIGUOUS"

    def test_trap_unrecoverable_all_null(self, load_fixture_with_meta):
        """time_value 전부 결측을 ACTUAL/AMBIGUOUS로 호도 금지 → UNRECOVERABLE."""
        df, meta, expected = load_fixture_with_meta("c0203", "trap_unrecoverable_all_null")
        result = detect_time_format(df, meta)
        assert result["a3_state"] == "UNRECOVERABLE"

    # --- routing traps (one per Q) ---

    def test_trap_q02_routing(self, load_fixture_with_meta):
        """AMBIGUOUS → Q02 (명시 routing assert)."""
        df, meta, expected = load_fixture_with_meta("c0203", "trap_q02_routing")
        result = detect_time_format(df, meta)
        assert result["a3_state"] == "AMBIGUOUS"
        assert result["pass"] is False
        assert result["route_to_q"] == "Q02"

    def test_trap_q12_routing(self, load_fixture_with_meta):
        """UNRECOVERABLE → Q12 (명시 routing assert; INVALID/Q 날조 금지)."""
        df, meta, expected = load_fixture_with_meta("c0203", "trap_q12_routing")
        result = detect_time_format(df, meta)
        assert result["a3_state"] == "UNRECOVERABLE"
        assert result["pass"] is False
        assert result["route_to_q"] == "Q12"


class TestC0205:
    """c0205 — A5 관측/BLQ 평가 (DETECT BLQ_TOKEN)

    postcondition_predicate:
        meta.get('a5_state') in ['CLEAN','BLQ-FLAGGED','BLQ-TEXT','BLQ-ZERO','MULTI-ANALYTE','LLOQ-CHANGED','MISSING-MDV1','BIOANALYTICAL-FINAL-FLAG-MISSING','ABOVE-ULOQ','ABOVE-ULOQ-NO-POLICY','REPLICATE-SAME-TIME','REPLICATE-NO-POLICY','BLQ-NO-POLICY','LLOQ-MISSING','ABSENT']

    srp_intent: DETECT BLQ_TOKEN
    kind: detect
    can_route_to_q: [Q01, Q15D]   (route_to_q ∈ {None, Q01, Q15D}; ABSENT→INVALID는 scope 밖 → route_to_q=None, provenance_gaps GAP-8)
    verify_visualization:
        pass_route_to: c0206
        fail_route_to: Q01
    """

    _POSTCOND = ['CLEAN','BLQ-FLAGGED','BLQ-TEXT','BLQ-ZERO','MULTI-ANALYTE','LLOQ-CHANGED','MISSING-MDV1','BIOANALYTICAL-FINAL-FLAG-MISSING','ABOVE-ULOQ','ABOVE-ULOQ-NO-POLICY','REPLICATE-SAME-TIME','REPLICATE-NO-POLICY','BLQ-NO-POLICY','LLOQ-MISSING','ABSENT']

    # --- 15 happy (one per a5_state) ---

    def test_happy_clean(self, load_fixture_with_meta):
        """결함 없는 관측 → CLEAN, pass(→c0206)."""
        df, meta, expected = load_fixture_with_meta("c0205", "happy_clean")
        result = detect_blq_token(df, meta)
        assert result["a5_state"] == expected["a5_state"]
        assert result["pass"] == expected["pass"]
        assert result["route_to_q"] == expected["route_to_q"]
        assert meta.get('a5_state') in ['CLEAN','BLQ-FLAGGED','BLQ-TEXT','BLQ-ZERO','MULTI-ANALYTE','LLOQ-CHANGED','MISSING-MDV1','BIOANALYTICAL-FINAL-FLAG-MISSING','ABOVE-ULOQ','ABOVE-ULOQ-NO-POLICY','REPLICATE-SAME-TIME','REPLICATE-NO-POLICY','BLQ-NO-POLICY','LLOQ-MISSING','ABSENT']

    def test_happy_blq_flagged(self, load_fixture_with_meta):
        """BLQ flag 컬럼 존재(정책 有) → BLQ-FLAGGED, pass."""
        df, meta, expected = load_fixture_with_meta("c0205", "happy_blq_flagged")
        result = detect_blq_token(df, meta)
        assert result["a5_state"] == expected["a5_state"]
        assert result["pass"] == expected["pass"]
        assert result["route_to_q"] == expected["route_to_q"]
        assert meta.get('a5_state') in ['CLEAN','BLQ-FLAGGED','BLQ-TEXT','BLQ-ZERO','MULTI-ANALYTE','LLOQ-CHANGED','MISSING-MDV1','BIOANALYTICAL-FINAL-FLAG-MISSING','ABOVE-ULOQ','ABOVE-ULOQ-NO-POLICY','REPLICATE-SAME-TIME','REPLICATE-NO-POLICY','BLQ-NO-POLICY','LLOQ-MISSING','ABSENT']

    def test_happy_blq_text(self, load_fixture_with_meta):
        """DV에 '<LLOQ' 텍스트 토큰 → BLQ-TEXT, pass."""
        df, meta, expected = load_fixture_with_meta("c0205", "happy_blq_text")
        result = detect_blq_token(df, meta)
        assert result["a5_state"] == expected["a5_state"]
        assert result["pass"] == expected["pass"]
        assert result["route_to_q"] == expected["route_to_q"]
        assert meta.get('a5_state') in ['CLEAN','BLQ-FLAGGED','BLQ-TEXT','BLQ-ZERO','MULTI-ANALYTE','LLOQ-CHANGED','MISSING-MDV1','BIOANALYTICAL-FINAL-FLAG-MISSING','ABOVE-ULOQ','ABOVE-ULOQ-NO-POLICY','REPLICATE-SAME-TIME','REPLICATE-NO-POLICY','BLQ-NO-POLICY','LLOQ-MISSING','ABSENT']

    def test_happy_blq_zero(self, load_fixture_with_meta):
        """BLQ를 0으로 표기(정책 有) → BLQ-ZERO, pass."""
        df, meta, expected = load_fixture_with_meta("c0205", "happy_blq_zero")
        result = detect_blq_token(df, meta)
        assert result["a5_state"] == expected["a5_state"]
        assert result["pass"] == expected["pass"]
        assert result["route_to_q"] == expected["route_to_q"]
        assert meta.get('a5_state') in ['CLEAN','BLQ-FLAGGED','BLQ-TEXT','BLQ-ZERO','MULTI-ANALYTE','LLOQ-CHANGED','MISSING-MDV1','BIOANALYTICAL-FINAL-FLAG-MISSING','ABOVE-ULOQ','ABOVE-ULOQ-NO-POLICY','REPLICATE-SAME-TIME','REPLICATE-NO-POLICY','BLQ-NO-POLICY','LLOQ-MISSING','ABSENT']

    def test_happy_multi_analyte(self, load_fixture_with_meta):
        """복수 analyte 관측 → MULTI-ANALYTE, pass."""
        df, meta, expected = load_fixture_with_meta("c0205", "happy_multi_analyte")
        result = detect_blq_token(df, meta)
        assert result["a5_state"] == expected["a5_state"]
        assert result["pass"] == expected["pass"]
        assert result["route_to_q"] == expected["route_to_q"]
        assert meta.get('a5_state') in ['CLEAN','BLQ-FLAGGED','BLQ-TEXT','BLQ-ZERO','MULTI-ANALYTE','LLOQ-CHANGED','MISSING-MDV1','BIOANALYTICAL-FINAL-FLAG-MISSING','ABOVE-ULOQ','ABOVE-ULOQ-NO-POLICY','REPLICATE-SAME-TIME','REPLICATE-NO-POLICY','BLQ-NO-POLICY','LLOQ-MISSING','ABSENT']

    def test_happy_lloq_changed(self, load_fixture_with_meta):
        """LLOQ 변경 이력 문서화됨 → LLOQ-CHANGED, pass."""
        df, meta, expected = load_fixture_with_meta("c0205", "happy_lloq_changed")
        result = detect_blq_token(df, meta)
        assert result["a5_state"] == expected["a5_state"]
        assert result["pass"] == expected["pass"]
        assert result["route_to_q"] == expected["route_to_q"]
        assert meta.get('a5_state') in ['CLEAN','BLQ-FLAGGED','BLQ-TEXT','BLQ-ZERO','MULTI-ANALYTE','LLOQ-CHANGED','MISSING-MDV1','BIOANALYTICAL-FINAL-FLAG-MISSING','ABOVE-ULOQ','ABOVE-ULOQ-NO-POLICY','REPLICATE-SAME-TIME','REPLICATE-NO-POLICY','BLQ-NO-POLICY','LLOQ-MISSING','ABSENT']

    def test_happy_missing_mdv1(self, load_fixture_with_meta):
        """관측 결측이 MDV=1로 처리됨 → MISSING-MDV1, pass(P4)."""
        df, meta, expected = load_fixture_with_meta("c0205", "happy_missing_mdv1")
        result = detect_blq_token(df, meta)
        assert result["a5_state"] == expected["a5_state"]
        assert result["pass"] == expected["pass"]
        assert result["route_to_q"] == expected["route_to_q"]
        assert meta.get('a5_state') in ['CLEAN','BLQ-FLAGGED','BLQ-TEXT','BLQ-ZERO','MULTI-ANALYTE','LLOQ-CHANGED','MISSING-MDV1','BIOANALYTICAL-FINAL-FLAG-MISSING','ABOVE-ULOQ','ABOVE-ULOQ-NO-POLICY','REPLICATE-SAME-TIME','REPLICATE-NO-POLICY','BLQ-NO-POLICY','LLOQ-MISSING','ABSENT']

    def test_happy_bioanalytical_final_flag_missing(self, load_fixture_with_meta):
        """재분석 최종결과 flag 부재 → BIOANALYTICAL-FINAL-FLAG-MISSING, Q15D."""
        df, meta, expected = load_fixture_with_meta("c0205", "happy_bioanalytical_final_flag_missing")
        result = detect_blq_token(df, meta)
        assert result["a5_state"] == expected["a5_state"]
        assert result["pass"] == expected["pass"]
        assert result["route_to_q"] == "Q15D"
        assert meta.get('a5_state') in ['CLEAN','BLQ-FLAGGED','BLQ-TEXT','BLQ-ZERO','MULTI-ANALYTE','LLOQ-CHANGED','MISSING-MDV1','BIOANALYTICAL-FINAL-FLAG-MISSING','ABOVE-ULOQ','ABOVE-ULOQ-NO-POLICY','REPLICATE-SAME-TIME','REPLICATE-NO-POLICY','BLQ-NO-POLICY','LLOQ-MISSING','ABSENT']

    def test_happy_above_uloq(self, load_fixture_with_meta):
        """ULOQ 초과(정책 有) → ABOVE-ULOQ, pass."""
        df, meta, expected = load_fixture_with_meta("c0205", "happy_above_uloq")
        result = detect_blq_token(df, meta)
        assert result["a5_state"] == expected["a5_state"]
        assert result["pass"] == expected["pass"]
        assert result["route_to_q"] == expected["route_to_q"]
        assert meta.get('a5_state') in ['CLEAN','BLQ-FLAGGED','BLQ-TEXT','BLQ-ZERO','MULTI-ANALYTE','LLOQ-CHANGED','MISSING-MDV1','BIOANALYTICAL-FINAL-FLAG-MISSING','ABOVE-ULOQ','ABOVE-ULOQ-NO-POLICY','REPLICATE-SAME-TIME','REPLICATE-NO-POLICY','BLQ-NO-POLICY','LLOQ-MISSING','ABSENT']

    def test_happy_above_uloq_no_policy(self, load_fixture_with_meta):
        """ULOQ 초과 + 정책 부재 → ABOVE-ULOQ-NO-POLICY, Q01(P1)."""
        df, meta, expected = load_fixture_with_meta("c0205", "happy_above_uloq_no_policy")
        result = detect_blq_token(df, meta)
        assert result["a5_state"] == expected["a5_state"]
        assert result["pass"] == expected["pass"]
        assert result["route_to_q"] == "Q01"
        assert meta.get('a5_state') in ['CLEAN','BLQ-FLAGGED','BLQ-TEXT','BLQ-ZERO','MULTI-ANALYTE','LLOQ-CHANGED','MISSING-MDV1','BIOANALYTICAL-FINAL-FLAG-MISSING','ABOVE-ULOQ','ABOVE-ULOQ-NO-POLICY','REPLICATE-SAME-TIME','REPLICATE-NO-POLICY','BLQ-NO-POLICY','LLOQ-MISSING','ABSENT']

    def test_happy_replicate_same_time(self, load_fixture_with_meta):
        """동일 (ID,TIME) 반복(정책 有) → REPLICATE-SAME-TIME, pass."""
        df, meta, expected = load_fixture_with_meta("c0205", "happy_replicate_same_time")
        result = detect_blq_token(df, meta)
        assert result["a5_state"] == expected["a5_state"]
        assert result["pass"] == expected["pass"]
        assert result["route_to_q"] == expected["route_to_q"]
        assert meta.get('a5_state') in ['CLEAN','BLQ-FLAGGED','BLQ-TEXT','BLQ-ZERO','MULTI-ANALYTE','LLOQ-CHANGED','MISSING-MDV1','BIOANALYTICAL-FINAL-FLAG-MISSING','ABOVE-ULOQ','ABOVE-ULOQ-NO-POLICY','REPLICATE-SAME-TIME','REPLICATE-NO-POLICY','BLQ-NO-POLICY','LLOQ-MISSING','ABSENT']

    def test_happy_replicate_no_policy(self, load_fixture_with_meta):
        """동일 (ID,TIME) 반복 + 정책 부재 → REPLICATE-NO-POLICY, Q01(P3)."""
        df, meta, expected = load_fixture_with_meta("c0205", "happy_replicate_no_policy")
        result = detect_blq_token(df, meta)
        assert result["a5_state"] == expected["a5_state"]
        assert result["pass"] == expected["pass"]
        assert result["route_to_q"] == "Q01"
        assert meta.get('a5_state') in ['CLEAN','BLQ-FLAGGED','BLQ-TEXT','BLQ-ZERO','MULTI-ANALYTE','LLOQ-CHANGED','MISSING-MDV1','BIOANALYTICAL-FINAL-FLAG-MISSING','ABOVE-ULOQ','ABOVE-ULOQ-NO-POLICY','REPLICATE-SAME-TIME','REPLICATE-NO-POLICY','BLQ-NO-POLICY','LLOQ-MISSING','ABSENT']

    def test_happy_blq_no_policy(self, load_fixture_with_meta):
        """BLQ 존재 + 처리정책 부재 → BLQ-NO-POLICY, Q01."""
        df, meta, expected = load_fixture_with_meta("c0205", "happy_blq_no_policy")
        result = detect_blq_token(df, meta)
        assert result["a5_state"] == expected["a5_state"]
        assert result["pass"] == expected["pass"]
        assert result["route_to_q"] == "Q01"
        assert meta.get('a5_state') in ['CLEAN','BLQ-FLAGGED','BLQ-TEXT','BLQ-ZERO','MULTI-ANALYTE','LLOQ-CHANGED','MISSING-MDV1','BIOANALYTICAL-FINAL-FLAG-MISSING','ABOVE-ULOQ','ABOVE-ULOQ-NO-POLICY','REPLICATE-SAME-TIME','REPLICATE-NO-POLICY','BLQ-NO-POLICY','LLOQ-MISSING','ABSENT']

    def test_happy_lloq_missing(self, load_fixture_with_meta):
        """LLOQ 수치 부재 → LLOQ-MISSING, Q01."""
        df, meta, expected = load_fixture_with_meta("c0205", "happy_lloq_missing")
        result = detect_blq_token(df, meta)
        assert result["a5_state"] == expected["a5_state"]
        assert result["pass"] == expected["pass"]
        assert result["route_to_q"] == "Q01"
        assert meta.get('a5_state') in ['CLEAN','BLQ-FLAGGED','BLQ-TEXT','BLQ-ZERO','MULTI-ANALYTE','LLOQ-CHANGED','MISSING-MDV1','BIOANALYTICAL-FINAL-FLAG-MISSING','ABOVE-ULOQ','ABOVE-ULOQ-NO-POLICY','REPLICATE-SAME-TIME','REPLICATE-NO-POLICY','BLQ-NO-POLICY','LLOQ-MISSING','ABSENT']

    def test_happy_absent(self, load_fixture_with_meta):
        """관측 자체가 부재 → ABSENT (scope 밖 INVALID, route_to_q=None — GAP-8)."""
        df, meta, expected = load_fixture_with_meta("c0205", "happy_absent")
        result = detect_blq_token(df, meta)
        assert result["a5_state"] == expected["a5_state"]
        assert result["route_to_q"] is None
        assert meta.get('a5_state') in ['CLEAN','BLQ-FLAGGED','BLQ-TEXT','BLQ-ZERO','MULTI-ANALYTE','LLOQ-CHANGED','MISSING-MDV1','BIOANALYTICAL-FINAL-FLAG-MISSING','ABOVE-ULOQ','ABOVE-ULOQ-NO-POLICY','REPLICATE-SAME-TIME','REPLICATE-NO-POLICY','BLQ-NO-POLICY','LLOQ-MISSING','ABSENT']

    # --- edge ---

    def test_edge_clean_df_fallback(self, load_fixture_with_meta):
        """선언 부재, DV 수치 정상 → CLEAN (df 추론)."""
        df, meta, expected = load_fixture_with_meta("c0205", "edge_clean_df_fallback")
        result = detect_blq_token(df, meta)
        assert result["a5_state"] == expected["a5_state"]
        assert result["pass"] == expected["pass"]
        assert meta.get('a5_state') in ['CLEAN','BLQ-FLAGGED','BLQ-TEXT','BLQ-ZERO','MULTI-ANALYTE','LLOQ-CHANGED','MISSING-MDV1','BIOANALYTICAL-FINAL-FLAG-MISSING','ABOVE-ULOQ','ABOVE-ULOQ-NO-POLICY','REPLICATE-SAME-TIME','REPLICATE-NO-POLICY','BLQ-NO-POLICY','LLOQ-MISSING','ABSENT']

    # --- 15 category traps (one per a5_state) ---

    def test_trap_clean_no_blq(self, load_fixture_with_meta):
        df, meta, expected = load_fixture_with_meta("c0205", "trap_clean_no_blq")
        result = detect_blq_token(df, meta)
        assert result["a5_state"] == "CLEAN"

    def test_trap_blq_flagged_vs_no_policy(self, load_fixture_with_meta):
        """BLQ flag(정책 有)가 BLQ-NO-POLICY로 silent 격하되면 안 됨 → BLQ-FLAGGED."""
        df, meta, expected = load_fixture_with_meta("c0205", "trap_blq_flagged_vs_no_policy")
        result = detect_blq_token(df, meta)
        assert result["a5_state"] == "BLQ-FLAGGED"

    def test_trap_blq_text_not_clean(self, load_fixture_with_meta):
        """DV의 '<LLOQ' 텍스트를 CLEAN으로 silent 통과 금지 → BLQ-TEXT."""
        df, meta, expected = load_fixture_with_meta("c0205", "trap_blq_text_not_clean")
        result = detect_blq_token(df, meta)
        assert result["a5_state"] == "BLQ-TEXT"

    def test_trap_blq_zero_vs_clean(self, load_fixture_with_meta):
        """0으로 표기된 BLQ를 CLEAN으로 silent 통과 금지 → BLQ-ZERO."""
        df, meta, expected = load_fixture_with_meta("c0205", "trap_blq_zero_vs_clean")
        result = detect_blq_token(df, meta)
        assert result["a5_state"] == "BLQ-ZERO"

    def test_trap_multi_analyte_vs_clean(self, load_fixture_with_meta):
        df, meta, expected = load_fixture_with_meta("c0205", "trap_multi_analyte_vs_clean")
        result = detect_blq_token(df, meta)
        assert result["a5_state"] == "MULTI-ANALYTE"

    def test_trap_lloq_changed_vs_missing(self, load_fixture_with_meta):
        """문서화된 LLOQ 변경을 LLOQ-MISSING으로 호도 금지 → LLOQ-CHANGED."""
        df, meta, expected = load_fixture_with_meta("c0205", "trap_lloq_changed_vs_missing")
        result = detect_blq_token(df, meta)
        assert result["a5_state"] == "LLOQ-CHANGED"

    def test_trap_missing_mdv1_vs_absent(self, load_fixture_with_meta):
        """MDV=1로 처리된 결측을 ABSENT로 silent 격하 금지 → MISSING-MDV1."""
        df, meta, expected = load_fixture_with_meta("c0205", "trap_missing_mdv1_vs_absent")
        result = detect_blq_token(df, meta)
        assert result["a5_state"] == "MISSING-MDV1"

    def test_trap_bioanalytical_final_flag_missing(self, load_fixture_with_meta):
        df, meta, expected = load_fixture_with_meta("c0205", "trap_bioanalytical_final_flag_missing")
        result = detect_blq_token(df, meta)
        assert result["a5_state"] == "BIOANALYTICAL-FINAL-FLAG-MISSING"

    def test_trap_above_uloq_vs_no_policy(self, load_fixture_with_meta):
        """ULOQ 초과(정책 有)가 -NO-POLICY로 silent 격하되면 안 됨 → ABOVE-ULOQ."""
        df, meta, expected = load_fixture_with_meta("c0205", "trap_above_uloq_vs_no_policy")
        result = detect_blq_token(df, meta)
        assert result["a5_state"] == "ABOVE-ULOQ"

    def test_trap_above_uloq_no_policy_q01(self, load_fixture_with_meta):
        df, meta, expected = load_fixture_with_meta("c0205", "trap_above_uloq_no_policy_q01")
        result = detect_blq_token(df, meta)
        assert result["a5_state"] == "ABOVE-ULOQ-NO-POLICY"

    def test_trap_replicate_same_time_vs_no_policy(self, load_fixture_with_meta):
        """반복 관측(정책 有)이 -NO-POLICY로 silent 격하되면 안 됨 → REPLICATE-SAME-TIME."""
        df, meta, expected = load_fixture_with_meta("c0205", "trap_replicate_same_time_vs_no_policy")
        result = detect_blq_token(df, meta)
        assert result["a5_state"] == "REPLICATE-SAME-TIME"

    def test_trap_replicate_no_policy_q01(self, load_fixture_with_meta):
        df, meta, expected = load_fixture_with_meta("c0205", "trap_replicate_no_policy_q01")
        result = detect_blq_token(df, meta)
        assert result["a5_state"] == "REPLICATE-NO-POLICY"

    def test_trap_blq_no_policy_q01(self, load_fixture_with_meta):
        df, meta, expected = load_fixture_with_meta("c0205", "trap_blq_no_policy_q01")
        result = detect_blq_token(df, meta)
        assert result["a5_state"] == "BLQ-NO-POLICY"

    def test_trap_lloq_missing_q01(self, load_fixture_with_meta):
        df, meta, expected = load_fixture_with_meta("c0205", "trap_lloq_missing_q01")
        result = detect_blq_token(df, meta)
        assert result["a5_state"] == "LLOQ-MISSING"

    def test_trap_absent_not_clean(self, load_fixture_with_meta):
        """DV 전부 결측을 CLEAN으로 silent 통과 금지 → ABSENT."""
        df, meta, expected = load_fixture_with_meta("c0205", "trap_absent_not_clean")
        result = detect_blq_token(df, meta)
        assert result["a5_state"] == "ABSENT"

    # --- routing traps (one per Q) ---

    def test_trap_q01_routing(self, load_fixture_with_meta):
        """BLQ-NO-POLICY → Q01 (명시 routing assert)."""
        df, meta, expected = load_fixture_with_meta("c0205", "trap_q01_routing")
        result = detect_blq_token(df, meta)
        assert result["a5_state"] == "BLQ-NO-POLICY"
        assert result["pass"] is False
        assert result["route_to_q"] == "Q01"

    def test_trap_q15d_routing(self, load_fixture_with_meta):
        """BIOANALYTICAL-FINAL-FLAG-MISSING → Q15D (명시 routing assert)."""
        df, meta, expected = load_fixture_with_meta("c0205", "trap_q15d_routing")
        result = detect_blq_token(df, meta)
        assert result["a5_state"] == "BIOANALYTICAL-FINAL-FLAG-MISSING"
        assert result["pass"] is False
        assert result["route_to_q"] == "Q15D"


class TestC0209:
    """c0209 — A9 데이터 결함 수리 가능성 평가 (VERIFY CROSS_COLUMN_INVARIANT, ※실제로는 A9 axis classifier)

    postcondition_predicate:
        meta.get('a9_state') in ['CLEAN','DUPLICATE-EXACT','UNSORTED','COLUMN-SYNONYM','UNIT-CONVERSION','ENCODING-FIX','PRE-DOSE-SAMPLE','PLANNED-VS-ACTUAL','PROTOCOL-DEVIATION','REANALYSIS-FINAL-DEFINED','REANALYSIS-FINAL-MISSING','PROTOCOL-DEVIATION-NO-POLICY','IRRECONCILABLE']

    srp_intent: VERIFY CROSS_COLUMN_INVARIANT
    kind: verify
    can_route_to_q: [Q06, Q15D]   (route_to_q ∈ {None, Q06, Q15D}; IRRECONCILABLE→INVALID 종착은 하류 ROUTE c — provenance_gaps GAP-12)
    verify_visualization:
        pass_route_to: c0210
        fail_route_to: Q06
    """

    # --- 13 happy (one per a9_state) ---

    def test_happy_clean(self, load_fixture_with_meta):
        """결함 없음 → CLEAN, pass(→c0210)."""
        df, meta, expected = load_fixture_with_meta("c0209", "happy_clean")
        result = verify_cross_column_invariant(df, meta)
        assert result["a9_state"] == expected["a9_state"]
        assert result["pass"] == expected["pass"]
        assert result["route_to_q"] == expected["route_to_q"]
        assert meta.get('a9_state') in ['CLEAN','DUPLICATE-EXACT','UNSORTED','COLUMN-SYNONYM','UNIT-CONVERSION','ENCODING-FIX','PRE-DOSE-SAMPLE','PLANNED-VS-ACTUAL','PROTOCOL-DEVIATION','REANALYSIS-FINAL-DEFINED','REANALYSIS-FINAL-MISSING','PROTOCOL-DEVIATION-NO-POLICY','IRRECONCILABLE']

    def test_happy_duplicate_exact(self, load_fixture_with_meta):
        """완전중복 행 존재 → DUPLICATE-EXACT, pass(REPAIR 제거)."""
        df, meta, expected = load_fixture_with_meta("c0209", "happy_duplicate_exact")
        result = verify_cross_column_invariant(df, meta)
        assert result["a9_state"] == expected["a9_state"]
        assert result["pass"] == expected["pass"]
        assert meta.get('a9_state') in ['CLEAN','DUPLICATE-EXACT','UNSORTED','COLUMN-SYNONYM','UNIT-CONVERSION','ENCODING-FIX','PRE-DOSE-SAMPLE','PLANNED-VS-ACTUAL','PROTOCOL-DEVIATION','REANALYSIS-FINAL-DEFINED','REANALYSIS-FINAL-MISSING','PROTOCOL-DEVIATION-NO-POLICY','IRRECONCILABLE']

    def test_happy_unsorted(self, load_fixture_with_meta):
        """id별 time 비오름차순 → UNSORTED, pass(REPAIR 정렬)."""
        df, meta, expected = load_fixture_with_meta("c0209", "happy_unsorted")
        result = verify_cross_column_invariant(df, meta)
        assert result["a9_state"] == expected["a9_state"]
        assert result["pass"] == expected["pass"]
        assert meta.get('a9_state') in ['CLEAN','DUPLICATE-EXACT','UNSORTED','COLUMN-SYNONYM','UNIT-CONVERSION','ENCODING-FIX','PRE-DOSE-SAMPLE','PLANNED-VS-ACTUAL','PROTOCOL-DEVIATION','REANALYSIS-FINAL-DEFINED','REANALYSIS-FINAL-MISSING','PROTOCOL-DEVIATION-NO-POLICY','IRRECONCILABLE']

    def test_happy_column_synonym(self, load_fixture_with_meta):
        """컬럼명 동의어 선언 → COLUMN-SYNONYM."""
        df, meta, expected = load_fixture_with_meta("c0209", "happy_column_synonym")
        result = verify_cross_column_invariant(df, meta)
        assert result["a9_state"] == expected["a9_state"]
        assert result["pass"] == expected["pass"]
        assert meta.get('a9_state') in ['CLEAN','DUPLICATE-EXACT','UNSORTED','COLUMN-SYNONYM','UNIT-CONVERSION','ENCODING-FIX','PRE-DOSE-SAMPLE','PLANNED-VS-ACTUAL','PROTOCOL-DEVIATION','REANALYSIS-FINAL-DEFINED','REANALYSIS-FINAL-MISSING','PROTOCOL-DEVIATION-NO-POLICY','IRRECONCILABLE']

    def test_happy_unit_conversion(self, load_fixture_with_meta):
        """단위 변환 필요(정책 有) → UNIT-CONVERSION."""
        df, meta, expected = load_fixture_with_meta("c0209", "happy_unit_conversion")
        result = verify_cross_column_invariant(df, meta)
        assert result["a9_state"] == expected["a9_state"]
        assert result["pass"] == expected["pass"]
        assert meta.get('a9_state') in ['CLEAN','DUPLICATE-EXACT','UNSORTED','COLUMN-SYNONYM','UNIT-CONVERSION','ENCODING-FIX','PRE-DOSE-SAMPLE','PLANNED-VS-ACTUAL','PROTOCOL-DEVIATION','REANALYSIS-FINAL-DEFINED','REANALYSIS-FINAL-MISSING','PROTOCOL-DEVIATION-NO-POLICY','IRRECONCILABLE']

    def test_happy_encoding_fix(self, load_fixture_with_meta):
        """인코딩 복구 필요 → ENCODING-FIX."""
        df, meta, expected = load_fixture_with_meta("c0209", "happy_encoding_fix")
        result = verify_cross_column_invariant(df, meta)
        assert result["a9_state"] == expected["a9_state"]
        assert result["pass"] == expected["pass"]
        assert meta.get('a9_state') in ['CLEAN','DUPLICATE-EXACT','UNSORTED','COLUMN-SYNONYM','UNIT-CONVERSION','ENCODING-FIX','PRE-DOSE-SAMPLE','PLANNED-VS-ACTUAL','PROTOCOL-DEVIATION','REANALYSIS-FINAL-DEFINED','REANALYSIS-FINAL-MISSING','PROTOCOL-DEVIATION-NO-POLICY','IRRECONCILABLE']

    def test_happy_pre_dose_sample(self, load_fixture_with_meta):
        """투여 전 채혈 처리(정책 有) → PRE-DOSE-SAMPLE."""
        df, meta, expected = load_fixture_with_meta("c0209", "happy_pre_dose_sample")
        result = verify_cross_column_invariant(df, meta)
        assert result["a9_state"] == expected["a9_state"]
        assert result["pass"] == expected["pass"]
        assert meta.get('a9_state') in ['CLEAN','DUPLICATE-EXACT','UNSORTED','COLUMN-SYNONYM','UNIT-CONVERSION','ENCODING-FIX','PRE-DOSE-SAMPLE','PLANNED-VS-ACTUAL','PROTOCOL-DEVIATION','REANALYSIS-FINAL-DEFINED','REANALYSIS-FINAL-MISSING','PROTOCOL-DEVIATION-NO-POLICY','IRRECONCILABLE']

    def test_happy_planned_vs_actual(self, load_fixture_with_meta):
        """planned/actual 불일치(정책 有) → PLANNED-VS-ACTUAL."""
        df, meta, expected = load_fixture_with_meta("c0209", "happy_planned_vs_actual")
        result = verify_cross_column_invariant(df, meta)
        assert result["a9_state"] == expected["a9_state"]
        assert result["pass"] == expected["pass"]
        assert meta.get('a9_state') in ['CLEAN','DUPLICATE-EXACT','UNSORTED','COLUMN-SYNONYM','UNIT-CONVERSION','ENCODING-FIX','PRE-DOSE-SAMPLE','PLANNED-VS-ACTUAL','PROTOCOL-DEVIATION','REANALYSIS-FINAL-DEFINED','REANALYSIS-FINAL-MISSING','PROTOCOL-DEVIATION-NO-POLICY','IRRECONCILABLE']

    def test_happy_protocol_deviation(self, load_fixture_with_meta):
        """프로토콜 일탈 + 처리 정책 有 → PROTOCOL-DEVIATION (pass)."""
        df, meta, expected = load_fixture_with_meta("c0209", "happy_protocol_deviation")
        result = verify_cross_column_invariant(df, meta)
        assert result["a9_state"] == expected["a9_state"]
        assert result["pass"] == expected["pass"]
        assert result["route_to_q"] is None
        assert meta.get('a9_state') in ['CLEAN','DUPLICATE-EXACT','UNSORTED','COLUMN-SYNONYM','UNIT-CONVERSION','ENCODING-FIX','PRE-DOSE-SAMPLE','PLANNED-VS-ACTUAL','PROTOCOL-DEVIATION','REANALYSIS-FINAL-DEFINED','REANALYSIS-FINAL-MISSING','PROTOCOL-DEVIATION-NO-POLICY','IRRECONCILABLE']

    def test_happy_reanalysis_final_defined(self, load_fixture_with_meta):
        """재분석 최종결과 정의됨 → REANALYSIS-FINAL-DEFINED (pass, REPAIR)."""
        df, meta, expected = load_fixture_with_meta("c0209", "happy_reanalysis_final_defined")
        result = verify_cross_column_invariant(df, meta)
        assert result["a9_state"] == expected["a9_state"]
        assert result["pass"] == expected["pass"]
        assert result["route_to_q"] is None
        assert meta.get('a9_state') in ['CLEAN','DUPLICATE-EXACT','UNSORTED','COLUMN-SYNONYM','UNIT-CONVERSION','ENCODING-FIX','PRE-DOSE-SAMPLE','PLANNED-VS-ACTUAL','PROTOCOL-DEVIATION','REANALYSIS-FINAL-DEFINED','REANALYSIS-FINAL-MISSING','PROTOCOL-DEVIATION-NO-POLICY','IRRECONCILABLE']

    def test_happy_reanalysis_final_missing(self, load_fixture_with_meta):
        """재분석 최종결과 미정 → REANALYSIS-FINAL-MISSING, Q15D."""
        df, meta, expected = load_fixture_with_meta("c0209", "happy_reanalysis_final_missing")
        result = verify_cross_column_invariant(df, meta)
        assert result["a9_state"] == expected["a9_state"]
        assert result["pass"] == expected["pass"]
        assert result["route_to_q"] == "Q15D"
        assert meta.get('a9_state') in ['CLEAN','DUPLICATE-EXACT','UNSORTED','COLUMN-SYNONYM','UNIT-CONVERSION','ENCODING-FIX','PRE-DOSE-SAMPLE','PLANNED-VS-ACTUAL','PROTOCOL-DEVIATION','REANALYSIS-FINAL-DEFINED','REANALYSIS-FINAL-MISSING','PROTOCOL-DEVIATION-NO-POLICY','IRRECONCILABLE']

    def test_happy_protocol_deviation_no_policy(self, load_fixture_with_meta):
        """프로토콜 일탈 + 처리 정책 부재 → PROTOCOL-DEVIATION-NO-POLICY, Q06."""
        df, meta, expected = load_fixture_with_meta("c0209", "happy_protocol_deviation_no_policy")
        result = verify_cross_column_invariant(df, meta)
        assert result["a9_state"] == expected["a9_state"]
        assert result["pass"] == expected["pass"]
        assert result["route_to_q"] == "Q06"
        assert meta.get('a9_state') in ['CLEAN','DUPLICATE-EXACT','UNSORTED','COLUMN-SYNONYM','UNIT-CONVERSION','ENCODING-FIX','PRE-DOSE-SAMPLE','PLANNED-VS-ACTUAL','PROTOCOL-DEVIATION','REANALYSIS-FINAL-DEFINED','REANALYSIS-FINAL-MISSING','PROTOCOL-DEVIATION-NO-POLICY','IRRECONCILABLE']

    def test_happy_irreconcilable(self, load_fixture_with_meta):
        """복구 불가 → IRRECONCILABLE (c0209 scope 내 route_to_q=None; INVALID 종착은 하류 ROUTE c)."""
        df, meta, expected = load_fixture_with_meta("c0209", "happy_irreconcilable")
        result = verify_cross_column_invariant(df, meta)
        assert result["a9_state"] == expected["a9_state"]
        assert result["route_to_q"] is None
        assert meta.get('a9_state') in ['CLEAN','DUPLICATE-EXACT','UNSORTED','COLUMN-SYNONYM','UNIT-CONVERSION','ENCODING-FIX','PRE-DOSE-SAMPLE','PLANNED-VS-ACTUAL','PROTOCOL-DEVIATION','REANALYSIS-FINAL-DEFINED','REANALYSIS-FINAL-MISSING','PROTOCOL-DEVIATION-NO-POLICY','IRRECONCILABLE']

    # --- edge ---

    def test_edge_minimal(self, load_fixture_with_meta):
        """최소 1행 결함 없음 → CLEAN (기본 경로)."""
        df, meta, expected = load_fixture_with_meta("c0209", "edge_minimal")
        result = verify_cross_column_invariant(df, meta)
        assert result["a9_state"] == expected["a9_state"]
        assert result["pass"] == expected["pass"]
        assert meta.get('a9_state') in ['CLEAN','DUPLICATE-EXACT','UNSORTED','COLUMN-SYNONYM','UNIT-CONVERSION','ENCODING-FIX','PRE-DOSE-SAMPLE','PLANNED-VS-ACTUAL','PROTOCOL-DEVIATION','REANALYSIS-FINAL-DEFINED','REANALYSIS-FINAL-MISSING','PROTOCOL-DEVIATION-NO-POLICY','IRRECONCILABLE']

    # --- category / routing traps ---

    def test_trap_q06_routing(self, load_fixture_with_meta):
        """PROTOCOL-DEVIATION-NO-POLICY → Q06 (명시 routing assert)."""
        df, meta, expected = load_fixture_with_meta("c0209", "trap_q06_routing")
        result = verify_cross_column_invariant(df, meta)
        assert result["a9_state"] == "PROTOCOL-DEVIATION-NO-POLICY"
        assert result["pass"] is False
        assert result["route_to_q"] == "Q06"

    def test_trap_q15d_routing(self, load_fixture_with_meta):
        """REANALYSIS-FINAL-MISSING → Q15D (명시 routing assert)."""
        df, meta, expected = load_fixture_with_meta("c0209", "trap_q15d_routing")
        result = verify_cross_column_invariant(df, meta)
        assert result["a9_state"] == "REANALYSIS-FINAL-MISSING"
        assert result["pass"] is False
        assert result["route_to_q"] == "Q15D"

    def test_trap_irreconcilable_no_q(self, load_fixture_with_meta):
        """IRRECONCILABLE은 can_route_to_q 밖 INVALID/Q를 날조하지 않는다 → route_to_q=None (GAP-12)."""
        df, meta, expected = load_fixture_with_meta("c0209", "trap_irreconcilable_no_q")
        result = verify_cross_column_invariant(df, meta)
        assert result["a9_state"] == "IRRECONCILABLE"
        assert result["route_to_q"] is None

    def test_trap_duplicate_vs_replicate(self, load_fixture_with_meta):
        """P3: 동일 (ID,TIME)에 다른 DV(정당 replicate, A5 소관)를 DUPLICATE-EXACT로 silent 제거 금지 → CLEAN."""
        df, meta, expected = load_fixture_with_meta("c0209", "trap_duplicate_vs_replicate")
        result = verify_cross_column_invariant(df, meta)
        assert result["a9_state"] == "CLEAN"
        assert result["route_to_q"] is None

    def test_trap_unsorted_not_clean(self, load_fixture_with_meta):
        """id별 time 역순을 CLEAN으로 silent 통과 금지 → UNSORTED."""
        df, meta, expected = load_fixture_with_meta("c0209", "trap_unsorted_not_clean")
        result = verify_cross_column_invariant(df, meta)
        assert result["a9_state"] == "UNSORTED"

    def test_trap_protocol_deviation_vs_no_policy(self, load_fixture_with_meta):
        """프로토콜 일탈(처리 정책 有)이 -NO-POLICY로 silent 격하되면 안 됨 → PROTOCOL-DEVIATION (pass)."""
        df, meta, expected = load_fixture_with_meta("c0209", "trap_protocol_deviation_vs_no_policy")
        result = verify_cross_column_invariant(df, meta)
        assert result["a9_state"] == "PROTOCOL-DEVIATION"
        assert result["route_to_q"] is None

    def test_trap_reanalysis_defined_vs_missing(self, load_fixture_with_meta):
        """재분석 최종결과 정의됨이 -MISSING으로 silent 격하되면 안 됨 → REANALYSIS-FINAL-DEFINED (pass)."""
        df, meta, expected = load_fixture_with_meta("c0209", "trap_reanalysis_defined_vs_missing")
        result = verify_cross_column_invariant(df, meta)
        assert result["a9_state"] == "REANALYSIS-FINAL-DEFINED"
        assert result["route_to_q"] is None

    def test_trap_whitespace_case(self, load_fixture_with_meta):
        """' Duplicate-Exact ' (공백·대소문자·구분자) → 정규화 후 DUPLICATE-EXACT."""
        df, meta, expected = load_fixture_with_meta("c0209", "trap_whitespace_case")
        result = verify_cross_column_invariant(df, meta)
        assert result["a9_state"] == "DUPLICATE-EXACT"

    def test_trap_clean_not_routed(self, load_fixture_with_meta):
        """CLEAN은 Q를 날조하지 않는다 → route_to_q=None."""
        df, meta, expected = load_fixture_with_meta("c0209", "trap_clean_not_routed")
        result = verify_cross_column_invariant(df, meta)
        assert result["a9_state"] == "CLEAN"
        assert result["route_to_q"] is None

    # --- 선언이 df full-row 완전중복(→DUPLICATE-EXACT) 신호를 이김 (AUDIT #2: 선언-직결 defect_state override trap) ---

    def test_trap_column_synonym_overrides_dup(self, load_fixture_with_meta):
        """full-row 완전중복(단독이면 DUPLICATE-EXACT)인데 defect_state=column-synonym 선언 → 선언 우선."""
        df, meta, expected = load_fixture_with_meta("c0209", "trap_column_synonym_overrides_dup")
        result = verify_cross_column_invariant(df, meta)
        assert result["a9_state"] == expected["a9_state"]
        assert result["a9_state"] == "COLUMN-SYNONYM"
        assert result["pass"] is True
        assert result["route_to_q"] is None

    def test_trap_unit_conversion_overrides_dup(self, load_fixture_with_meta):
        """full-row 완전중복(단독이면 DUPLICATE-EXACT)인데 defect_state=unit-conversion 선언 → 선언 우선."""
        df, meta, expected = load_fixture_with_meta("c0209", "trap_unit_conversion_overrides_dup")
        result = verify_cross_column_invariant(df, meta)
        assert result["a9_state"] == expected["a9_state"]
        assert result["a9_state"] == "UNIT-CONVERSION"
        assert result["pass"] is True
        assert result["route_to_q"] is None

    def test_trap_encoding_fix_overrides_dup(self, load_fixture_with_meta):
        """full-row 완전중복(단독이면 DUPLICATE-EXACT)인데 defect_state=encoding-fix 선언 → 선언 우선."""
        df, meta, expected = load_fixture_with_meta("c0209", "trap_encoding_fix_overrides_dup")
        result = verify_cross_column_invariant(df, meta)
        assert result["a9_state"] == expected["a9_state"]
        assert result["a9_state"] == "ENCODING-FIX"
        assert result["pass"] is True
        assert result["route_to_q"] is None

    def test_trap_pre_dose_sample_overrides_dup(self, load_fixture_with_meta):
        """full-row 완전중복(단독이면 DUPLICATE-EXACT)인데 defect_state=pre-dose-sample 선언 → 선언 우선."""
        df, meta, expected = load_fixture_with_meta("c0209", "trap_pre_dose_sample_overrides_dup")
        result = verify_cross_column_invariant(df, meta)
        assert result["a9_state"] == expected["a9_state"]
        assert result["a9_state"] == "PRE-DOSE-SAMPLE"
        assert result["pass"] is True
        assert result["route_to_q"] is None

    def test_trap_planned_vs_actual_overrides_dup(self, load_fixture_with_meta):
        """full-row 완전중복(단독이면 DUPLICATE-EXACT)인데 defect_state=planned-vs-actual 선언 → 선언 우선."""
        df, meta, expected = load_fixture_with_meta("c0209", "trap_planned_vs_actual_overrides_dup")
        result = verify_cross_column_invariant(df, meta)
        assert result["a9_state"] == expected["a9_state"]
        assert result["a9_state"] == "PLANNED-VS-ACTUAL"
        assert result["pass"] is True
        assert result["route_to_q"] is None


class TestC0210:
    """c0210 — A10 소스 형식 파싱 가능성 평가 (DETECT FILE_FORMAT)

    postcondition_predicate:
        meta.get('a10_state') in ['SDTM-ADaM','EDC-STRUCTURED','CRO-VENDOR','FLAT-TABULAR','LEGACY-NM','SEMI-STRUCTURED','NON-TABULAR','CORRUPTED']

    srp_intent: DETECT FILE_FORMAT
    kind: detect
    can_route_to_q: []   (순수 분류기 — route_to_q 항상 None, pass 항상 True; q_codes A10 참조 0건)
    verify_visualization:
        pass_route_to: "next axis"   (route_to_q None)
        fail_route_to: "UNSUPPORTED/INVALID"  (= NON-TABULAR→UNSUPPORTED / CORRUPTED→INVALID;
            §2 terminal, Q-code 아님 → scope-밖, 하류 ROUTE c 책임 — provenance_gaps GAP-13)
    선언 1차(meta['file_format']|['source_format']) → df fallback FLAT-TABULAR(1-of-8 한계, GAP-13).
    """

    # --- 8 happy (one per a10_state, 선언 descriptor) ---

    def test_happy_sdtm_adam(self, load_fixture_with_meta):
        """SDTM-ADaM 선언 → SDTM-ADaM, pass(→next axis)."""
        df, meta, expected = load_fixture_with_meta("c0210", "happy_sdtm_adam")
        result = detect_source_format(df, meta)
        assert result["a10_state"] == expected["a10_state"]
        assert result["pass"] == expected["pass"]
        assert result["route_to_q"] == expected["route_to_q"]
        assert result["route_to_q"] is None  # verify_visualization pass → next axis
        assert meta.get('a10_state') in ['SDTM-ADaM','EDC-STRUCTURED','CRO-VENDOR','FLAT-TABULAR','LEGACY-NM','SEMI-STRUCTURED','NON-TABULAR','CORRUPTED']

    def test_happy_edc_structured(self, load_fixture_with_meta):
        """EDC-STRUCTURED 선언 → EDC-STRUCTURED, pass."""
        df, meta, expected = load_fixture_with_meta("c0210", "happy_edc_structured")
        result = detect_source_format(df, meta)
        assert result["a10_state"] == expected["a10_state"]
        assert result["pass"] == expected["pass"]
        assert result["route_to_q"] == expected["route_to_q"]
        assert meta.get('a10_state') in ['SDTM-ADaM','EDC-STRUCTURED','CRO-VENDOR','FLAT-TABULAR','LEGACY-NM','SEMI-STRUCTURED','NON-TABULAR','CORRUPTED']

    def test_happy_cro_vendor(self, load_fixture_with_meta):
        """CRO-VENDOR 선언 → CRO-VENDOR, pass."""
        df, meta, expected = load_fixture_with_meta("c0210", "happy_cro_vendor")
        result = detect_source_format(df, meta)
        assert result["a10_state"] == expected["a10_state"]
        assert result["pass"] == expected["pass"]
        assert result["route_to_q"] == expected["route_to_q"]
        assert meta.get('a10_state') in ['SDTM-ADaM','EDC-STRUCTURED','CRO-VENDOR','FLAT-TABULAR','LEGACY-NM','SEMI-STRUCTURED','NON-TABULAR','CORRUPTED']

    def test_happy_flat_tabular(self, load_fixture_with_meta):
        """FLAT-TABULAR 선언 → FLAT-TABULAR, pass."""
        df, meta, expected = load_fixture_with_meta("c0210", "happy_flat_tabular")
        result = detect_source_format(df, meta)
        assert result["a10_state"] == expected["a10_state"]
        assert result["pass"] == expected["pass"]
        assert result["route_to_q"] == expected["route_to_q"]
        assert meta.get('a10_state') in ['SDTM-ADaM','EDC-STRUCTURED','CRO-VENDOR','FLAT-TABULAR','LEGACY-NM','SEMI-STRUCTURED','NON-TABULAR','CORRUPTED']

    def test_happy_legacy_nm(self, load_fixture_with_meta):
        """LEGACY-NM 선언 → LEGACY-NM, pass."""
        df, meta, expected = load_fixture_with_meta("c0210", "happy_legacy_nm")
        result = detect_source_format(df, meta)
        assert result["a10_state"] == expected["a10_state"]
        assert result["pass"] == expected["pass"]
        assert result["route_to_q"] == expected["route_to_q"]
        assert meta.get('a10_state') in ['SDTM-ADaM','EDC-STRUCTURED','CRO-VENDOR','FLAT-TABULAR','LEGACY-NM','SEMI-STRUCTURED','NON-TABULAR','CORRUPTED']

    def test_happy_semi_structured(self, load_fixture_with_meta):
        """SEMI-STRUCTURED 선언 → SEMI-STRUCTURED, pass."""
        df, meta, expected = load_fixture_with_meta("c0210", "happy_semi_structured")
        result = detect_source_format(df, meta)
        assert result["a10_state"] == expected["a10_state"]
        assert result["pass"] == expected["pass"]
        assert result["route_to_q"] == expected["route_to_q"]
        assert meta.get('a10_state') in ['SDTM-ADaM','EDC-STRUCTURED','CRO-VENDOR','FLAT-TABULAR','LEGACY-NM','SEMI-STRUCTURED','NON-TABULAR','CORRUPTED']

    def test_happy_non_tabular(self, load_fixture_with_meta):
        """NON-TABULAR 선언 → NON-TABULAR(분류만; →UNSUPPORTED는 하류 ROUTE c, route_to_q=None)."""
        df, meta, expected = load_fixture_with_meta("c0210", "happy_non_tabular")
        result = detect_source_format(df, meta)
        assert result["a10_state"] == expected["a10_state"]
        assert result["pass"] == expected["pass"]
        assert result["route_to_q"] == expected["route_to_q"]
        assert result["route_to_q"] is None  # NON-TABULAR→UNSUPPORTED scope-out (GAP-13)
        assert meta.get('a10_state') in ['SDTM-ADaM','EDC-STRUCTURED','CRO-VENDOR','FLAT-TABULAR','LEGACY-NM','SEMI-STRUCTURED','NON-TABULAR','CORRUPTED']

    def test_happy_corrupted(self, load_fixture_with_meta):
        """CORRUPTED 선언 → CORRUPTED(분류만; →INVALID는 하류 ROUTE c, route_to_q=None)."""
        df, meta, expected = load_fixture_with_meta("c0210", "happy_corrupted")
        result = detect_source_format(df, meta)
        assert result["a10_state"] == expected["a10_state"]
        assert result["pass"] == expected["pass"]
        assert result["route_to_q"] == expected["route_to_q"]
        assert result["route_to_q"] is None  # CORRUPTED→INVALID scope-out (GAP-13)
        assert meta.get('a10_state') in ['SDTM-ADaM','EDC-STRUCTURED','CRO-VENDOR','FLAT-TABULAR','LEGACY-NM','SEMI-STRUCTURED','NON-TABULAR','CORRUPTED']

    # --- 2 edge (선언 부재 → df fallback FLAT-TABULAR; GAP-13 한계) ---

    def test_edge_flat_tabular_df_fallback(self, load_fixture_with_meta):
        """선언 부재 + 파싱된 df → FLAT-TABULAR(기본값, 1-of-8 한계)."""
        df, meta, expected = load_fixture_with_meta("c0210", "edge_flat_tabular_df_fallback")
        result = detect_source_format(df, meta)
        assert result["a10_state"] == expected["a10_state"]
        assert result["pass"] == expected["pass"]
        assert meta.get('a10_state') in ['SDTM-ADaM','EDC-STRUCTURED','CRO-VENDOR','FLAT-TABULAR','LEGACY-NM','SEMI-STRUCTURED','NON-TABULAR','CORRUPTED']

    def test_edge_file_exists_no_rows(self, load_fixture_with_meta):
        """file_exists=True + 최소 df, 선언 부재 → FLAT-TABULAR(deterministic, 날조 없음)."""
        df, meta, expected = load_fixture_with_meta("c0210", "edge_file_exists_no_rows")
        result = detect_source_format(df, meta)
        assert result["a10_state"] == expected["a10_state"]
        assert result["pass"] == expected["pass"]
        assert meta.get('a10_state') in ['SDTM-ADaM','EDC-STRUCTURED','CRO-VENDOR','FLAT-TABULAR','LEGACY-NM','SEMI-STRUCTURED','NON-TABULAR','CORRUPTED']

    # --- 8 trap (선언이 generic df 기본값을 이김 / scope-out 명시) ---

    def test_trap_sdtm_adam_vs_flat(self, load_fixture_with_meta):
        """SDTM-ADaM 선언이 평범한 df 때문에 FLAT-TABULAR로 silent 격하되면 안 됨 → SDTM-ADaM."""
        df, meta, expected = load_fixture_with_meta("c0210", "trap_sdtm_adam_vs_flat")
        result = detect_source_format(df, meta)
        assert result["a10_state"] == "SDTM-ADaM"
        assert result["route_to_q"] is None

    def test_trap_edc_structured_vs_flat(self, load_fixture_with_meta):
        """EDC-STRUCTURED 선언이 FLAT-TABULAR로 silent 격하되면 안 됨 → EDC-STRUCTURED."""
        df, meta, expected = load_fixture_with_meta("c0210", "trap_edc_structured_vs_flat")
        result = detect_source_format(df, meta)
        assert result["a10_state"] == "EDC-STRUCTURED"
        assert result["route_to_q"] is None

    def test_trap_cro_vendor_vs_flat(self, load_fixture_with_meta):
        """CRO-VENDOR 선언이 FLAT-TABULAR로 silent 격하되면 안 됨 → CRO-VENDOR."""
        df, meta, expected = load_fixture_with_meta("c0210", "trap_cro_vendor_vs_flat")
        result = detect_source_format(df, meta)
        assert result["a10_state"] == "CRO-VENDOR"
        assert result["route_to_q"] is None

    def test_trap_legacy_nm_vs_flat(self, load_fixture_with_meta):
        """LEGACY-NM 선언이 FLAT-TABULAR로 silent 격하되면 안 됨 → LEGACY-NM."""
        df, meta, expected = load_fixture_with_meta("c0210", "trap_legacy_nm_vs_flat")
        result = detect_source_format(df, meta)
        assert result["a10_state"] == "LEGACY-NM"
        assert result["route_to_q"] is None

    def test_trap_semi_structured_vs_flat(self, load_fixture_with_meta):
        """SEMI-STRUCTURED 선언이 FLAT-TABULAR로 silent 격하되면 안 됨 → SEMI-STRUCTURED."""
        df, meta, expected = load_fixture_with_meta("c0210", "trap_semi_structured_vs_flat")
        result = detect_source_format(df, meta)
        assert result["a10_state"] == "SEMI-STRUCTURED"
        assert result["route_to_q"] is None

    def test_trap_non_tabular_scope_out(self, load_fixture_with_meta):
        """NON-TABULAR을 FLAT-TABULAR로 silent 격상 금지 → NON-TABULAR, route_to_q=None(scope-out)."""
        df, meta, expected = load_fixture_with_meta("c0210", "trap_non_tabular_scope_out")
        result = detect_source_format(df, meta)
        assert result["a10_state"] == "NON-TABULAR"
        assert result["route_to_q"] is None

    def test_trap_corrupted_scope_out(self, load_fixture_with_meta):
        """CORRUPTED를 FLAT-TABULAR로 silent 격상 금지 → CORRUPTED, route_to_q=None(scope-out)."""
        df, meta, expected = load_fixture_with_meta("c0210", "trap_corrupted_scope_out")
        result = detect_source_format(df, meta)
        assert result["a10_state"] == "CORRUPTED"
        assert result["route_to_q"] is None

    def test_trap_unknown_descriptor_fallback(self, load_fixture_with_meta):
        """미지의 선언이 out-of-vocab state를 만들거나 crash하면 안 됨 → FLAT-TABULAR."""
        df, meta, expected = load_fixture_with_meta("c0210", "trap_unknown_descriptor_fallback")
        result = detect_source_format(df, meta)
        assert result["a10_state"] == "FLAT-TABULAR"
        assert result["route_to_q"] is None


class TestC0019:
    """c0019 — TIME 표준화 (ASSIGN TIME)

    postcondition_predicate:
        'TIME' in df.columns and df['TIME'].apply(lambda x: isinstance(x, (int, float, np.floating, np.integer))).all() and df['TIME'].notna().all()

    srp_intent: ASSIGN TIME
    kind: transform
    requires_detection_by: c0203
    can_route_to_q: [Q02, Q12]

    설계(사용자 확정): spec python_snippet 1:1 — to_numeric(time_value). a3_state는 라우팅 게이트로만
    사용(AMBIGUOUS→Q02, UNRECOVERABLE→Q12). 6개 유도가능 state는 동일 derivation(spec에 없는
    per-state 산문 derivation 금지). 입력계약: time_value 생산자=상류 mess c 미구현 — GAP-18(↔GAP-7).
    """

    def _check_postcond(self, df):
        assert 'TIME' in df.columns and df['TIME'].apply(lambda x: isinstance(x, (int, float, np.floating, np.integer))).all() and df['TIME'].notna().all()

    # --- 6 happy (one per 유도가능 a3_state; 전부 동일 derivation = numeric(time_value)) ---

    def test_happy_actual(self, load_fixture_with_meta):
        """ACTUAL: time_value → numeric TIME."""
        df, meta, expected = load_fixture_with_meta("c0019", "happy_actual")
        result = assign_time(df, meta)
        assert result["success"] == expected["success"]
        df_out = result["df"]
        self._check_postcond(df_out)
        assert list(df_out["TIME"]) == expected["TIME"]

    def test_happy_actual_preferred(self, load_fixture_with_meta):
        """ACTUAL-PREFERRED: 동일 derivation(time_value)."""
        df, meta, expected = load_fixture_with_meta("c0019", "happy_actual_preferred")
        result = assign_time(df, meta)
        assert result["success"] == expected["success"]
        df_out = result["df"]
        self._check_postcond(df_out)
        assert list(df_out["TIME"]) == expected["TIME"]

    def test_happy_nominal_only(self, load_fixture_with_meta):
        """NOMINAL-ONLY: spec에 없는 nominal_time derivation 금지 — time_value 그대로."""
        df, meta, expected = load_fixture_with_meta("c0019", "happy_nominal_only")
        result = assign_time(df, meta)
        assert result["success"] == expected["success"]
        df_out = result["df"]
        self._check_postcond(df_out)
        assert list(df_out["TIME"]) == expected["TIME"]

    def test_happy_nominal_preferred(self, load_fixture_with_meta):
        """NOMINAL-PREFERRED: 동일 derivation."""
        df, meta, expected = load_fixture_with_meta("c0019", "happy_nominal_preferred")
        result = assign_time(df, meta)
        assert result["success"] == expected["success"]
        df_out = result["df"]
        self._check_postcond(df_out)
        assert list(df_out["TIME"]) == expected["TIME"]

    def test_happy_elapsed(self, load_fixture_with_meta):
        """ELAPSED: spec에 없는 offset derivation 금지 — time_value 그대로(상류서 이미 정규화)."""
        df, meta, expected = load_fixture_with_meta("c0019", "happy_elapsed")
        result = assign_time(df, meta)
        assert result["success"] == expected["success"]
        df_out = result["df"]
        self._check_postcond(df_out)
        assert list(df_out["TIME"]) == expected["TIME"]

    def test_happy_interval(self, load_fixture_with_meta):
        """INTERVAL: spec snippet 따름(time_value) — midpoint 산문 derivation 금지."""
        df, meta, expected = load_fixture_with_meta("c0019", "happy_interval")
        result = assign_time(df, meta)
        assert result["success"] == expected["success"]
        df_out = result["df"]
        self._check_postcond(df_out)
        assert list(df_out["TIME"]) == expected["TIME"]

    # --- 1 edge ---

    def test_edge_minimal(self, load_fixture_with_meta):
        """최소 1행, ACTUAL → TIME=[0.0]."""
        df, meta, expected = load_fixture_with_meta("c0019", "edge_minimal")
        result = assign_time(df, meta)
        assert result["success"] == expected["success"]
        df_out = result["df"]
        self._check_postcond(df_out)
        assert list(df_out["TIME"]) == expected["TIME"]

    # --- 5 trap (2 routing + 3 silent-error) ---

    def test_trap_ambiguous(self, load_fixture_with_meta):
        """a3_state=AMBIGUOUS → fail, Q02 (라우팅; derivation 안 함)."""
        df, meta, expected = load_fixture_with_meta("c0019", "trap_ambiguous")
        result = assign_time(df, meta)
        assert result["success"] == expected["success"]
        assert result["route_to_q"] == expected["route_to_q"]

    def test_trap_unrecoverable(self, load_fixture_with_meta):
        """a3_state=UNRECOVERABLE → fail, Q12."""
        df, meta, expected = load_fixture_with_meta("c0019", "trap_unrecoverable")
        result = assign_time(df, meta)
        assert result["success"] == expected["success"]
        assert result["route_to_q"] == expected["route_to_q"]

    def test_trap_parse_nan(self, load_fixture_with_meta):
        """time_value 결측 → TIME NaN silent 통과 금지 → fail, Q02."""
        df, meta, expected = load_fixture_with_meta("c0019", "trap_parse_nan")
        result = assign_time(df, meta)
        assert result["success"] == expected["success"]
        assert result["route_to_q"] == expected["route_to_q"]

    def test_trap_parse_text(self, load_fixture_with_meta):
        """파싱 불가 문자 토큰 → fail, Q02."""
        df, meta, expected = load_fixture_with_meta("c0019", "trap_parse_text")
        result = assign_time(df, meta)
        assert result["success"] == expected["success"]
        assert result["route_to_q"] == expected["route_to_q"]

    def test_trap_negative(self, load_fixture_with_meta):
        """음수 시간(numeric·notna여서 postcond는 통과) → 도메인 위반 fail, Q02."""
        df, meta, expected = load_fixture_with_meta("c0019", "trap_negative")
        result = assign_time(df, meta)
        assert result["success"] == expected["success"]
        assert result["route_to_q"] == expected["route_to_q"]


class TestC0020:
    """c0020 — BLQ_FLAG 부여 (ASSIGN BLQ_FLAG)

    postcondition_predicate:
        ('BLQ_FLAG' not in df.columns) or (df['BLQ_FLAG'].isin([0,1]).all() and (df.loc[df['BLQ_FLAG']==1, 'EVID']==0).all())

    srp_intent: ASSIGN BLQ_FLAG
    kind: transform
    requires_detection_by: c0205
    can_route_to_q: [Q01]

    설계(plan): blq_policy enum 분기 — M3/M4 → BLQ_FLAG 컬럼 생성(blq_detected→int),
    M1(제외)/M5(대체) → 컬럼 미생성(postcond 1번째 disjunct). a5_state는 라우팅 게이트
    (None/BLQ-NO-POLICY → Q01)이며 policy 분기보다 선행. silent-error: BLQ_FLAG=1이
    dose행(EVID≠0)에 붙으면 fail+Q01. 입력계약: blq_detected/blq_policy 생산자=c0306(미구현)/
    외부 — provenance_gaps GAP-15(DECISION-D3). 단위테스트는 fixture로 주입.
    """

    def _check_postcond(self, df):
        assert ('BLQ_FLAG' not in df.columns) or (df['BLQ_FLAG'].isin([0,1]).all() and (df.loc[df['BLQ_FLAG']==1, 'EVID']==0).all())

    # --- 4 happy (blq_policy 분기 전수: M3/M4 컬럼 생성, M1/M5 컬럼 미생성) ---

    def test_happy_m3(self, load_fixture_with_meta):
        """M3(likelihood): blq_detected → BLQ_FLAG int [0,1,0]."""
        df, meta, expected = load_fixture_with_meta("c0020", "happy_m3")
        result = assign_blq_flag(df, meta)
        assert result["success"] == expected["success"]
        df_out = result["df"]
        self._check_postcond(df_out)
        assert list(df_out["BLQ_FLAG"]) == expected["BLQ_FLAG"]

    def test_happy_m4(self, load_fixture_with_meta):
        """M4(likelihood): M3와 동일 컬럼 생성 경로."""
        df, meta, expected = load_fixture_with_meta("c0020", "happy_m4")
        result = assign_blq_flag(df, meta)
        assert result["success"] == expected["success"]
        df_out = result["df"]
        self._check_postcond(df_out)
        assert list(df_out["BLQ_FLAG"]) == expected["BLQ_FLAG"]

    def test_happy_m1(self, load_fixture_with_meta):
        """M1(exclusion): BLQ_FLAG 컬럼 미생성, success."""
        df, meta, expected = load_fixture_with_meta("c0020", "happy_m1")
        result = assign_blq_flag(df, meta)
        assert result["success"] == expected["success"]
        df_out = result["df"]
        self._check_postcond(df_out)
        assert "BLQ_FLAG" not in df_out.columns

    def test_happy_m5(self, load_fixture_with_meta):
        """M5(substitution): BLQ_FLAG 컬럼 미생성, success."""
        df, meta, expected = load_fixture_with_meta("c0020", "happy_m5")
        result = assign_blq_flag(df, meta)
        assert result["success"] == expected["success"]
        df_out = result["df"]
        self._check_postcond(df_out)
        assert "BLQ_FLAG" not in df_out.columns

    # --- 1 edge ---

    def test_edge_single_obs_m3(self, load_fixture_with_meta):
        """최소 1 obs, blq_detected True → BLQ_FLAG=[1]."""
        df, meta, expected = load_fixture_with_meta("c0020", "edge_single_obs_m3")
        result = assign_blq_flag(df, meta)
        assert result["success"] == expected["success"]
        df_out = result["df"]
        self._check_postcond(df_out)
        assert list(df_out["BLQ_FLAG"]) == expected["BLQ_FLAG"]

    # --- 3 trap (routing-gate + precond-gate + silent-error) ---

    def test_trap_no_evid(self, load_fixture_with_meta):
        """EVID 컬럼 부재 → fail, Q01."""
        df, meta, expected = load_fixture_with_meta("c0020", "trap_no_evid")
        result = assign_blq_flag(df, meta)
        assert result["success"] == expected["success"]
        assert result["route_to_q"] == expected["route_to_q"]

    def test_trap_blq_no_policy(self, load_fixture_with_meta):
        """a5_state=BLQ-NO-POLICY → fail, Q01 (policy 분기보다 선행하는 게이트)."""
        df, meta, expected = load_fixture_with_meta("c0020", "trap_blq_no_policy")
        result = assign_blq_flag(df, meta)
        assert result["success"] == expected["success"]
        assert result["route_to_q"] == expected["route_to_q"]

    def test_trap_blq_on_dose(self, load_fixture_with_meta):
        """M3인데 BLQ_FLAG=1이 dose행(EVID=1)에 붙음 → silent-error 차단, fail Q01."""
        df, meta, expected = load_fixture_with_meta("c0020", "trap_blq_on_dose")
        result = assign_blq_flag(df, meta)
        assert result["success"] == expected["success"]
        assert result["route_to_q"] == expected["route_to_q"]


class TestC0021:
    """c0021 — LLOQ 부여 (ASSIGN LLOQ)

    postcondition_predicate:
        ('LLOQ' not in df.columns) or ((df.loc[df['EVID']==0, 'LLOQ'] > 0).all() and (df.loc[df.get('BLQ_FLAG', pd.Series())==1, 'LLOQ'] > 0).all() if 'BLQ_FLAG' in df.columns else True)

    srp_intent: ASSIGN LLOQ
    kind: transform
    requires_detection_by: c0205
    can_route_to_q: [Q01]

    설계(plan): 분기 변수 = 'BLQ_FLAG' in df.columns (c0020 형제 산출의 런타임 존재) — c0020의
    blq_policy enum 분기와 구조가 달라 D-G4상 1:1(batch 아님). BLQ_FLAG 존재 시 LLOQ를
    pd.to_numeric(lloq_value, coerce)로 생성(c0019 선례 방어적 변환); obs행·BLQ행에 대해
    Guard1(NaN: 비수치/결측을 >0 비교 *전에* 명시 차단)→Guard2(≤0)로 순차 검사, 위반 시 fail+Q01.
    dose행(EVID≠0)은 postcond·guard 모두 미제약(NaN 허용). BLQ_FLAG 부재 → LLOQ 미생성(M1/M5 하류).
    precond gate: BLQ_FLAG 존재 + a5_state=LLOQ-MISSING → Q01. c0205_passed는 orchestrator 보장(D-S1).
    입력계약: lloq_value(←c0306 미구현)/BLQ_FLAG(←c0020 형제) — provenance_gaps GAP-15(DECISION-D3).
    단위테스트는 fixture로 주입.
    """

    def _check_postcond(self, df):
        assert ('LLOQ' not in df.columns) or ((df.loc[df['EVID']==0, 'LLOQ'] > 0).all() and (df.loc[df.get('BLQ_FLAG', pd.Series())==1, 'LLOQ'] > 0).all() if 'BLQ_FLAG' in df.columns else True)

    # --- 2 happy (BLQ_FLAG 존재/부재 분기) + 1 edge ---

    def test_happy_with_blq_flag(self, load_fixture_with_meta):
        """BLQ_FLAG 존재, obs/BLQ lloq 0.1 → LLOQ=[0.1,0.1]."""
        df, meta, expected = load_fixture_with_meta("c0021", "happy_with_blq_flag")
        result = assign_lloq(df, meta)
        assert result["success"] == expected["success"]
        df_out = result["df"]
        self._check_postcond(df_out)
        assert list(df_out["LLOQ"]) == expected["LLOQ"]

    def test_happy_no_blq_flag(self, load_fixture_with_meta):
        """BLQ_FLAG 부재 → LLOQ 컬럼 미생성, success."""
        df, meta, expected = load_fixture_with_meta("c0021", "happy_no_blq_flag")
        result = assign_lloq(df, meta)
        assert result["success"] == expected["success"]
        df_out = result["df"]
        self._check_postcond(df_out)
        assert "LLOQ" not in df_out.columns

    def test_edge_single_obs(self, load_fixture_with_meta):
        """최소 1 obs, BLQ_FLAG 존재, lloq 0.1 → LLOQ=[0.1]."""
        df, meta, expected = load_fixture_with_meta("c0021", "edge_single_obs")
        result = assign_lloq(df, meta)
        assert result["success"] == expected["success"]
        df_out = result["df"]
        self._check_postcond(df_out)
        assert list(df_out["LLOQ"]) == expected["LLOQ"]

    # --- 6 trap (no-evid + state-gate + 4 silent-error: text/blank→Guard1, zero/negative→Guard2) ---

    def test_trap_no_evid(self, load_fixture_with_meta):
        """EVID 컬럼 부재 → fail, Q01."""
        df, meta, expected = load_fixture_with_meta("c0021", "trap_no_evid")
        result = assign_lloq(df, meta)
        assert result["success"] == expected["success"]
        assert result["route_to_q"] == expected["route_to_q"]

    def test_trap_lloq_missing_state(self, load_fixture_with_meta):
        """BLQ_FLAG 존재 + a5_state=LLOQ-MISSING → precond gate, fail Q01 (값은 유효; state 게이트)."""
        df, meta, expected = load_fixture_with_meta("c0021", "trap_lloq_missing_state")
        result = assign_lloq(df, meta)
        assert result["success"] == expected["success"]
        assert result["route_to_q"] == expected["route_to_q"]

    def test_trap_lloq_text(self, load_fixture_with_meta):
        """obs lloq 비수치 토큰 → coerce NaN → Guard1(>0 비교 전 차단), fail Q01 (silent-error)."""
        df, meta, expected = load_fixture_with_meta("c0021", "trap_lloq_text")
        result = assign_lloq(df, meta)
        assert result["success"] == expected["success"]
        assert result["route_to_q"] == expected["route_to_q"]

    def test_trap_lloq_blank(self, load_fixture_with_meta):
        """obs lloq 결측(blank) → NaN → Guard1, fail Q01 (silent-error)."""
        df, meta, expected = load_fixture_with_meta("c0021", "trap_lloq_blank")
        result = assign_lloq(df, meta)
        assert result["success"] == expected["success"]
        assert result["route_to_q"] == expected["route_to_q"]

    def test_trap_lloq_zero(self, load_fixture_with_meta):
        """obs lloq=0 → Guard1 통과 후 Guard2(≤0), fail Q01 (silent-error)."""
        df, meta, expected = load_fixture_with_meta("c0021", "trap_lloq_zero")
        result = assign_lloq(df, meta)
        assert result["success"] == expected["success"]
        assert result["route_to_q"] == expected["route_to_q"]

    def test_trap_lloq_negative(self, load_fixture_with_meta):
        """obs lloq=-0.1 → Guard2(≤0), fail Q01 (silent-error)."""
        df, meta, expected = load_fixture_with_meta("c0021", "trap_lloq_negative")
        result = assign_lloq(df, meta)
        assert result["success"] == expected["success"]
        assert result["route_to_q"] == expected["route_to_q"]


class TestC0022:
    """c0022 — 기저 공변량 수치 코딩 (ASSIGN BASELINE_COVARIATE)

    postcondition_predicate:
        all(df[cov].apply(lambda x: isinstance(x, (int, float, np.floating, np.integer)) or pd.isna(x) == False).all() for cov in meta.get('baseline_covariates', []))

    srp_intent: ASSIGN BASELINE_COVARIATE
    kind: transform
    requires_detection_by: c0207
    can_route_to_q: [Q07, Q13]

    설계(사용자 ★★★ 확정 — IMPUTE override): spec python_snippet의 fillna(median())은 미준수.
    vocabulary.md §A 전역 규칙(IMPUTE 제외) > 개별 snippet. 결측 공변량은 median 대입 없이
    명시 NaN 보존(FLAG) + Q07 라우팅; 결측 없는 정상 공변량만 numeric ASSIGN(범주형 SEX→int,
    연속형→to_numeric coerce). axis gate(D-S4): KEY-MISSING→Q13, POLICY-MISSING→Q07(c0021 동형).
    마커 컬럼 미추가 → output_schema_delta 준수. ★verbatim postcond는 NaN-as-float를 통과(결측 0
    미강제)하므로 fillna 미준수가 postcond 위반 아님. 입력계약: baseline_covariates 리스트 생산자
    부재(GAP-3) — fixture 주입; snippet↔vocab 불일치 provenance_gaps GAP-19.
    """

    def _check_postcond(self, df, meta):
        assert all(df[cov].apply(lambda x: isinstance(x, (int, float, np.floating, np.integer)) or pd.isna(x) == False).all() for cov in meta.get('baseline_covariates', []))

    # --- 3 happy + 1 edge (결측 없는 정상 공변량 numeric 코딩) ---

    def test_happy_baseline_clean(self, load_fixture_with_meta):
        """BASELINE-CLEAN: 연속형 WT 실수 + 범주형 SEX(M/F)→int(0/1)."""
        df, meta, expected = load_fixture_with_meta("c0022", "happy_baseline_clean")
        result = assign_baseline_covariate(df, meta)
        assert result["success"] == expected["success"]
        df_out = result["df"]
        self._check_postcond(df_out, meta)
        assert list(df_out["WT"]) == expected["WT"]
        assert list(df_out["SEX"]) == expected["SEX"]

    def test_happy_continuous(self, load_fixture_with_meta):
        """연속형만(WT, AGE) → to_numeric 실수 그대로."""
        df, meta, expected = load_fixture_with_meta("c0022", "happy_continuous")
        result = assign_baseline_covariate(df, meta)
        assert result["success"] == expected["success"]
        df_out = result["df"]
        self._check_postcond(df_out, meta)
        assert list(df_out["WT"]) == expected["WT"]
        assert list(df_out["AGE"]) == expected["AGE"]

    def test_happy_categorical_sex(self, load_fixture_with_meta):
        """범주형 SEX(M/F/M) → int 코딩 [0,1,0]."""
        df, meta, expected = load_fixture_with_meta("c0022", "happy_categorical_sex")
        result = assign_baseline_covariate(df, meta)
        assert result["success"] == expected["success"]
        df_out = result["df"]
        self._check_postcond(df_out, meta)
        assert list(df_out["SEX"]) == expected["SEX"]

    def test_edge_single_row(self, load_fixture_with_meta):
        """최소 1행, WT 실수 + SEX→0."""
        df, meta, expected = load_fixture_with_meta("c0022", "edge_single_row")
        result = assign_baseline_covariate(df, meta)
        assert result["success"] == expected["success"]
        df_out = result["df"]
        self._check_postcond(df_out, meta)
        assert list(df_out["WT"]) == expected["WT"]
        assert list(df_out["SEX"]) == expected["SEX"]

    # --- 4 trap (2 axis-gate routing + 2 silent-error: median 대입 금지) ---

    def test_trap_policy_missing(self, load_fixture_with_meta):
        """a7_state=POLICY-MISSING → fail, Q07 (axis gate)."""
        df, meta, expected = load_fixture_with_meta("c0022", "trap_policy_missing")
        result = assign_baseline_covariate(df, meta)
        assert result["success"] == expected["success"]
        assert result["route_to_q"] == expected["route_to_q"]

    def test_trap_key_missing(self, load_fixture_with_meta):
        """a7_state=KEY-MISSING → fail, Q13 (axis gate; external linkage key)."""
        df, meta, expected = load_fixture_with_meta("c0022", "trap_key_missing")
        result = assign_baseline_covariate(df, meta)
        assert result["success"] == expected["success"]
        assert result["route_to_q"] == expected["route_to_q"]

    def test_trap_missing_wt(self, load_fixture_with_meta):
        """★ 결측 WT를 median으로 silent 채우지 않고 NaN 보존 + Q07 (IMPUTE 금지 핵심 trap)."""
        df, meta, expected = load_fixture_with_meta("c0022", "trap_missing_wt")
        result = assign_baseline_covariate(df, meta)
        assert result["success"] == expected["success"]
        assert result["route_to_q"] == expected["route_to_q"]

    def test_trap_unmapped_sex(self, load_fixture_with_meta):
        """매핑 불가 SEX('U') → NaN(날조 금지) → fail Q07."""
        df, meta, expected = load_fixture_with_meta("c0022", "trap_unmapped_sex")
        result = assign_baseline_covariate(df, meta)
        assert result["success"] == expected["success"]
        assert result["route_to_q"] == expected["route_to_q"]


class TestC0023:
    """c0023 — 시변 공변량 수치 코딩 (ASSIGN TIME_VARYING_COVARIATE)

    postcondition_predicate:
        all(df[cov].apply(lambda x: isinstance(x, (int, float, np.floating, np.integer))).all() for cov in meta.get('tv_covariates', []))

    srp_intent: ASSIGN TIME_VARYING_COVARIATE
    kind: transform
    requires_detection_by: c0207
    can_route_to_q: [Q07]

    설계(plan): spec snippet df.groupby('ID')[cov].ffill() = LOCF. vocabulary.md §A V10 PROPAGATE
    ("forward-fill, carry-forward")가 정의하는 정당 연산 — 자의적 IMPUTE(§A 금지)와 구분(관측값을
    동일 subject 내 전파). 따라서 c0022의 FLAG-우선 override 불필요(ffill 정당). to_numeric(coerce,
    c0019 선례) 후 within-ID ffill. LOCF로 채울 수 없는 leading 결측(직전 관측 부재)은 정책 필요→Q07.
    structural gate: 'ID' 부재→Q07(groupby 키; c0021 EVID 게이트 동형). axis gate: POLICY-MISSING→Q07.
    핵심 silent-error: cross-ID bleed 금지(groupby 없이 ffill하면 타 subject 값 오염). 입력계약:
    tv_covariates 리스트 생산자 부재(GAP-3) — fixture 주입. groupby 키 'ID'(L-1→L-2 가용) vs
    c0141 subject_id 불일치는 GAP-17.
    """

    def _check_postcond(self, df, meta):
        assert all(df[cov].apply(lambda x: isinstance(x, (int, float, np.floating, np.integer))).all() for cov in meta.get('tv_covariates', []))

    # --- 2 happy + 1 edge (within-ID LOCF = PROPAGATE) ---

    def test_happy_locf_fill(self, load_fixture_with_meta):
        """TIME-VARYING: 중간 결측을 직전 관측으로 carry-forward [70,.,65]→[70,70,65] (spec toy)."""
        df, meta, expected = load_fixture_with_meta("c0023", "happy_locf_fill")
        result = assign_time_varying_covariate(df, meta)
        assert result["success"] == expected["success"]
        df_out = result["df"]
        self._check_postcond(df_out, meta)
        assert list(df_out["WT"]) == expected["WT"]

    def test_happy_multi_subject(self, load_fixture_with_meta):
        """2 subject: 각 ID 내에서만 ffill(cross-ID 오염 없음)."""
        df, meta, expected = load_fixture_with_meta("c0023", "happy_multi_subject")
        result = assign_time_varying_covariate(df, meta)
        assert result["success"] == expected["success"]
        df_out = result["df"]
        self._check_postcond(df_out, meta)
        assert list(df_out["WT"]) == expected["WT"]

    def test_edge_single_row(self, load_fixture_with_meta):
        """최소 1행, 결측 없음 → WT=[70.0]."""
        df, meta, expected = load_fixture_with_meta("c0023", "edge_single_row")
        result = assign_time_varying_covariate(df, meta)
        assert result["success"] == expected["success"]
        df_out = result["df"]
        self._check_postcond(df_out, meta)
        assert list(df_out["WT"]) == expected["WT"]

    # --- 3 trap (axis-gate + LOCF 미충족 residual missing → Q07) ---

    def test_trap_policy_missing(self, load_fixture_with_meta):
        """a7_state=POLICY-MISSING → fail, Q07 (axis gate)."""
        df, meta, expected = load_fixture_with_meta("c0023", "trap_policy_missing")
        result = assign_time_varying_covariate(df, meta)
        assert result["success"] == expected["success"]
        assert result["route_to_q"] == expected["route_to_q"]

    def test_trap_leading_missing(self, load_fixture_with_meta):
        """leading 결측(직전 관측 부재) → ffill 미충족 → fail Q07 (bfill/mean 날조 금지)."""
        df, meta, expected = load_fixture_with_meta("c0023", "trap_leading_missing")
        result = assign_time_varying_covariate(df, meta)
        assert result["success"] == expected["success"]
        assert result["route_to_q"] == expected["route_to_q"]

    def test_trap_all_missing_cov(self, load_fixture_with_meta):
        """공변량 전체 결측 → carry-forward 불가 → fail Q07."""
        df, meta, expected = load_fixture_with_meta("c0023", "trap_all_missing_cov")
        result = assign_time_varying_covariate(df, meta)
        assert result["success"] == expected["success"]
        assert result["route_to_q"] == expected["route_to_q"]


class TestC0140:
    """c0140 — 기저 공변량 부착 (ASSIGN BASELINE_COVARIATE, L-2→L-3)

    postcondition_predicate:
        all(df.groupby('subject_id')[cov].first().notna().all() for cov in meta.get('baseline_covariates', [])) if meta.get('a7_state') != 'NONE-REQUIRED' else True

    srp_intent: ASSIGN BASELINE_COVARIATE
    kind: transform
    requires_detection_by: c0207
    can_route_to_q: [Q07]

    설계(사용자 ★★★ 확정): L-2→L-3 baseline 부착. c0022(L-1→L-2 형제) + GAP-17/19 구현 레벨 적용.
    GAP-17: TIME 부재 시 time_value==0 fallback(df.get('TIME')), groupby 키 subject_id→ID. GAP-19:
    결측 baseline은 median 대입 없이 NaN 보존 + Q07(자의적 IMPUTE 금지). 마커 컬럼 미추가(output_schema 준수).
    postcond 통과는 관측 baseline의 within-subject PROPAGATE로만(§A V10, c0023 동형; cross-subject bleed 금지).
    GAP-20(a): .first()=skipna → subject당 ≥1 관측 요구(결측0 아님) → IMPUTE 불요. verbatim postcond는
    happy/edge에만 assert(trap 출력엔 미호출), no-baseline subject는 Q07(c0022/c0023 선례). 입력계약:
    baseline_covariates 리스트 생산자 부재(GAP-3) — fixture 주입; spec snippet frozen(GAP-19 구현 override).
    """

    def _check_postcond(self, df, meta):
        assert all(df.groupby('subject_id')[cov].first().notna().all() for cov in meta.get('baseline_covariates', [])) if meta.get('a7_state') != 'NONE-REQUIRED' else True

    # --- 3 happy + 3 edge (관측 baseline within-subject PROPAGATE) ---

    def test_happy_baseline_clean(self, load_fixture_with_meta):
        """BASELINE-CLEAN: subject baseline(time_value==0) 값을 전 행에 전파(WT 희소행 채움 + SEX→int)."""
        df, meta, expected = load_fixture_with_meta("c0140", "happy_baseline_clean")
        result = assign_baseline_covariate_l3(df, meta)
        assert result["success"] == expected["success"]
        df_out = result["df"]
        self._check_postcond(df_out, meta)
        assert list(df_out["WT"]) == expected["WT"]
        assert list(df_out["SEX"]) == expected["SEX"]

    def test_happy_continuous(self, load_fixture_with_meta):
        """연속형 WT(희소)+AGE → baseline 전파."""
        df, meta, expected = load_fixture_with_meta("c0140", "happy_continuous")
        result = assign_baseline_covariate_l3(df, meta)
        assert result["success"] == expected["success"]
        df_out = result["df"]
        self._check_postcond(df_out, meta)
        assert list(df_out["WT"]) == expected["WT"]
        assert list(df_out["AGE"]) == expected["AGE"]

    def test_happy_categorical_sex(self, load_fixture_with_meta):
        """범주형 SEX(M/F/M)→int(0/1/0) baseline 전파."""
        df, meta, expected = load_fixture_with_meta("c0140", "happy_categorical_sex")
        result = assign_baseline_covariate_l3(df, meta)
        assert result["success"] == expected["success"]
        df_out = result["df"]
        self._check_postcond(df_out, meta)
        assert list(df_out["SEX"]) == expected["SEX"]

    def test_edge_single_row(self, load_fixture_with_meta):
        """최소 1행(baseline 1개) → WT 실수 + SEX→0."""
        df, meta, expected = load_fixture_with_meta("c0140", "edge_single_row")
        result = assign_baseline_covariate_l3(df, meta)
        assert result["success"] == expected["success"]
        df_out = result["df"]
        self._check_postcond(df_out, meta)
        assert list(df_out["WT"]) == expected["WT"]
        assert list(df_out["SEX"]) == expected["SEX"]

    def test_edge_time_column_present(self, load_fixture_with_meta):
        """GAP-17: TIME 컬럼 존재 시 TIME==0로 baseline 식별(time_value 없이도 동작)."""
        df, meta, expected = load_fixture_with_meta("c0140", "edge_time_column_present")
        result = assign_baseline_covariate_l3(df, meta)
        assert result["success"] == expected["success"]
        df_out = result["df"]
        self._check_postcond(df_out, meta)
        assert list(df_out["WT"]) == expected["WT"]

    def test_edge_none_required(self, load_fixture_with_meta):
        """a7_state=NONE-REQUIRED → postcond 단락(True), 공변량 부착 없이 success."""
        df, meta, expected = load_fixture_with_meta("c0140", "edge_none_required")
        result = assign_baseline_covariate_l3(df, meta)
        assert result["success"] == expected["success"]
        self._check_postcond(result["df"], meta)

    # --- 3 trap (axis-gate + GAP-19 no-impute + 매핑불가 → Q07; _check_postcond 미호출) ---

    def test_trap_policy_missing(self, load_fixture_with_meta):
        """a7_state=POLICY-MISSING → fail Q07 (axis gate)."""
        df, meta, expected = load_fixture_with_meta("c0140", "trap_policy_missing")
        result = assign_baseline_covariate_l3(df, meta)
        assert result["success"] == expected["success"]
        assert result["route_to_q"] == expected["route_to_q"]

    def test_trap_no_baseline(self, load_fixture_with_meta):
        """★ baseline 전무 subject → median 날조 없이 NaN 보존 + Q07 (GAP-19 핵심)."""
        df, meta, expected = load_fixture_with_meta("c0140", "trap_no_baseline")
        result = assign_baseline_covariate_l3(df, meta)
        assert result["success"] == expected["success"]
        assert result["route_to_q"] == expected["route_to_q"]

    def test_trap_unmapped_sex(self, load_fixture_with_meta):
        """매핑 불가 SEX('U') baseline → NaN(날조 금지) → fail Q07."""
        df, meta, expected = load_fixture_with_meta("c0140", "trap_unmapped_sex")
        result = assign_baseline_covariate_l3(df, meta)
        assert result["success"] == expected["success"]
        assert result["route_to_q"] == expected["route_to_q"]


class TestC0141:
    """c0141 — 시변 공변량 부착 (ASSIGN TIME_VARYING_COVARIATE, L-2→L-3)

    postcondition_predicate:
        all(df[cov].notna().all() for cov in meta.get('tv_covariates', []))

    srp_intent: ASSIGN TIME_VARYING_COVARIATE
    kind: transform
    requires_detection_by: c0207
    can_route_to_q: [Q07]

    설계(c0023 L-1→L-2 형제 동형 — key='subject_id'): within-subject LOCF(df.groupby('subject_id')[cov].ffill())
    = vocabulary.md §A V10 PROPAGATE(정당; 자의적 IMPUTE 아님 → c0022 FLAG-우선 override 불요). leading
    결측(직전 관측 부재)은 carry-forward 대상 없어 정책 필요 → Q07(bfill/mean 날조 금지). structural gate:
    'subject_id' 부재→Q07(c0023 'ID' 대비, GAP-17). axis gate: POLICY-MISSING→Q07. 핵심 silent-error:
    cross-subject bleed 금지(groupby 없는 ffill은 타 subject 오염). 입력계약: tv_covariates 생산자 부재(GAP-3) — fixture 주입.
    """

    def _check_postcond(self, df, meta):
        assert all(df[cov].notna().all() for cov in meta.get('tv_covariates', []))

    # --- 2 happy + 1 edge (within-subject LOCF = PROPAGATE) ---

    def test_happy_locf_fill(self, load_fixture_with_meta):
        """TIME-VARYING: 중간 결측을 직전 관측으로 carry-forward [70,.,65]→[70,70,65]."""
        df, meta, expected = load_fixture_with_meta("c0141", "happy_locf_fill")
        result = assign_time_varying_covariate_l3(df, meta)
        assert result["success"] == expected["success"]
        df_out = result["df"]
        self._check_postcond(df_out, meta)
        assert list(df_out["WT"]) == expected["WT"]

    def test_happy_multi_subject(self, load_fixture_with_meta):
        """2 subject: 각 subject_id 내에서만 ffill(cross-subject 오염 없음)."""
        df, meta, expected = load_fixture_with_meta("c0141", "happy_multi_subject")
        result = assign_time_varying_covariate_l3(df, meta)
        assert result["success"] == expected["success"]
        df_out = result["df"]
        self._check_postcond(df_out, meta)
        assert list(df_out["WT"]) == expected["WT"]

    def test_edge_single_row(self, load_fixture_with_meta):
        """최소 1행, 결측 없음 → WT=[70.0]."""
        df, meta, expected = load_fixture_with_meta("c0141", "edge_single_row")
        result = assign_time_varying_covariate_l3(df, meta)
        assert result["success"] == expected["success"]
        df_out = result["df"]
        self._check_postcond(df_out, meta)
        assert list(df_out["WT"]) == expected["WT"]

    # --- 3 trap (axis-gate + LOCF 미충족 residual missing → Q07; _check_postcond 미호출) ---

    def test_trap_policy_missing(self, load_fixture_with_meta):
        """a7_state=POLICY-MISSING → fail, Q07 (axis gate)."""
        df, meta, expected = load_fixture_with_meta("c0141", "trap_policy_missing")
        result = assign_time_varying_covariate_l3(df, meta)
        assert result["success"] == expected["success"]
        assert result["route_to_q"] == expected["route_to_q"]

    def test_trap_leading_missing(self, load_fixture_with_meta):
        """leading 결측(직전 관측 부재) → ffill 미충족 → fail Q07 (bfill/mean 날조 금지)."""
        df, meta, expected = load_fixture_with_meta("c0141", "trap_leading_missing")
        result = assign_time_varying_covariate_l3(df, meta)
        assert result["success"] == expected["success"]
        assert result["route_to_q"] == expected["route_to_q"]

    def test_trap_all_missing_cov(self, load_fixture_with_meta):
        """공변량 전체 결측 → carry-forward 불가 → fail Q07."""
        df, meta, expected = load_fixture_with_meta("c0141", "trap_all_missing_cov")
        result = assign_time_varying_covariate_l3(df, meta)
        assert result["success"] == expected["success"]
        assert result["route_to_q"] == expected["route_to_q"]


class TestC0121:
    """c0121 — 공변량 레이아웃 변환 (PIVOT COVARIATE_LAYOUT, L-2→L-3)

    postcondition_predicate:
        all(df[col].apply(lambda x: not isinstance(x, (list, dict))).all() for col in meta.get('covariate_columns', []))

    srp_intent: PIVOT COVARIATE_LAYOUT
    kind: transform
    requires_detection_by: c0207 (명목; 실효 detection = c0380/c0381 미구현, GAP-16)
    can_route_to_q: []

    설계(사용자 ★★★ 확정): 출력 shape = REFINED wide→long. verbatim postcond가 plural
    meta['covariate_columns']를 순회하며 base별 값 컬럼(df['WT'], df['AGE'])을 요구 → refined만 충족,
    plain melt(단일 cov_value, spec python_snippet/r_snippet)는 postcond 위반 → 미준수(snippet frozen,
    postcond 우선; GAP-19 선례, GAP-21 기록). WT_V1,WT_V2 → 'visit' 컬럼 + 'WT' 값 컬럼. multi-cov는
    별도 컬럼(혼합 금지). 분기키 cov_layout(∈{wide,long,none})는 c0380/c0381(미구현)이 생산(GAP-16) —
    fixture로 직접 주입. c0207_passed는 orchestrator 구조 보장(D-S1) — 함수 내 미검사(c0022/c0140 동형).
    ★silent no-op 방지(Lock 3): cov_layout 부재/미인식 → fail, route_to_q=None(can_route_to_q=[] →
    scope-out None, 날조 금지). pivot 무결성: ID×visit 행 수 정확, 값 손실/중복 0. 입력계약: GAP-16/GAP-21.
    """

    def _check_postcond(self, df, meta):
        assert all(df[col].apply(lambda x: not isinstance(x, (list, dict))).all() for col in meta.get('covariate_columns', []))

    # --- 3 happy (refined wide→long pivot) ---

    def test_happy_wide_single_cov(self, load_fixture_with_meta):
        """toy: 단일 공변량 wide(WT_V1,WT_V2) → long(visit 컬럼 + WT 값 컬럼)."""
        df, meta, expected = load_fixture_with_meta("c0121", "happy_wide_single_cov")
        result = pivot_covariate_layout(df, meta)
        assert result["success"] == expected["success"]
        df_out = result["df"]
        self._check_postcond(df_out, meta)
        assert list(df_out["WT"]) == expected["WT"]
        assert list(df_out["visit"]) == expected["visit"]
        assert len(df_out) == 4

    def test_happy_wide_multi_cov(self, load_fixture_with_meta):
        """multi-cov(WT_V*,AGE_V*) → 별도 WT,AGE 컬럼(한 컬럼 혼합 금지; cov_value 미생성)."""
        df, meta, expected = load_fixture_with_meta("c0121", "happy_wide_multi_cov")
        result = pivot_covariate_layout(df, meta)
        assert result["success"] == expected["success"]
        df_out = result["df"]
        self._check_postcond(df_out, meta)
        assert "cov_value" not in df_out.columns
        assert list(df_out["WT"]) == expected["WT"]
        assert list(df_out["AGE"]) == expected["AGE"]

    def test_happy_long_passthrough(self, load_fixture_with_meta):
        """cov_layout='long' → 이미 long, pass-through(불변 success)."""
        df, meta, expected = load_fixture_with_meta("c0121", "happy_long_passthrough")
        result = pivot_covariate_layout(df, meta)
        assert result["success"] == expected["success"]
        df_out = result["df"]
        self._check_postcond(df_out, meta)
        assert list(df_out["WT"]) == expected["WT"]

    # --- 2 edge ---

    def test_edge_none(self, load_fixture_with_meta):
        """cov_layout='none' → 공변량 없음, pass-through success(postcond 단락)."""
        df, meta, expected = load_fixture_with_meta("c0121", "edge_none")
        result = pivot_covariate_layout(df, meta)
        assert result["success"] == expected["success"]
        self._check_postcond(result["df"], meta)

    def test_edge_single_visit(self, load_fixture_with_meta):
        """단일 subject·단일 visit(WT_V1) → 1행 long."""
        df, meta, expected = load_fixture_with_meta("c0121", "edge_single_visit")
        result = pivot_covariate_layout(df, meta)
        assert result["success"] == expected["success"]
        df_out = result["df"]
        self._check_postcond(df_out, meta)
        assert list(df_out["WT"]) == expected["WT"]
        assert list(df_out["visit"]) == expected["visit"]

    # --- 3 trap (silent no-op 방지 + scope-out None; _check_postcond 미호출) ---

    def test_trap_cov_layout_missing(self, load_fixture_with_meta):
        """★ cov_layout 부재 → silent no-op 금지: fail, route_to_q=None(GAP-16)."""
        df, meta, expected = load_fixture_with_meta("c0121", "trap_cov_layout_missing")
        result = pivot_covariate_layout(df, meta)
        assert result["success"] == expected["success"]
        assert result["route_to_q"] == expected["route_to_q"]

    def test_trap_unrecognized_layout(self, load_fixture_with_meta):
        """cov_layout 미인식 값 → fail, route_to_q=None(scope-out 날조 금지, can_route_to_q=[])."""
        df, meta, expected = load_fixture_with_meta("c0121", "trap_unrecognized_layout")
        result = pivot_covariate_layout(df, meta)
        assert result["success"] == expected["success"]
        assert result["route_to_q"] == expected["route_to_q"]

    def test_trap_wide_no_covariates(self, load_fixture_with_meta):
        """cov_layout='wide'이나 pivot 대상 공변량 컬럼 부재 → fail, route_to_q=None(빈 분기 통과 금지)."""
        df, meta, expected = load_fixture_with_meta("c0121", "trap_wide_no_covariates")
        result = pivot_covariate_layout(df, meta)
        assert result["success"] == expected["success"]
        assert result["route_to_q"] == expected["route_to_q"]


# ===== Phase 5 · Slice 2 — TIME family =====

class TestC0213:
    """c0213 — 시간 기준점 검증 (VERIFY TIME_ANCHOR)

    postcondition_predicate:
        meta.get('time_anchor_consistent', True)

    srp_intent: VERIFY TIME_ANCHOR
    kind: verify
    requires_detection_by: null
    can_route_to_q: ['Q02']
    verify_visualization:
        pass_route_to: c0203
        fail_route_to: Q02
    """

    def test_happy(self, load_fixture_with_meta):
        """단일 유형 anchor('Day 1/2/3') → consistent=True, pass→c0203 (route None)."""
        df, meta, expected = load_fixture_with_meta("c0213", "happy")
        result = verify_time_anchor(df, meta)
        assert result["time_anchor_consistent"] == expected["time_anchor_consistent"]
        assert result["pass"] == expected["pass"]
        assert result["route_to_q"] == expected["route_to_q"]
        assert meta.get('time_anchor_consistent', True)

    def test_edge(self, load_fixture_with_meta):
        """anchor 토큰 부재(time_value만) → 날조 없이 기본 consistent=True (scope-out)."""
        df, meta, expected = load_fixture_with_meta("c0213", "edge")
        result = verify_time_anchor(df, meta)
        assert result["time_anchor_consistent"] == expected["time_anchor_consistent"]
        assert result["pass"] == expected["pass"]
        assert meta.get('time_anchor_consistent', True)

    def test_trap(self, load_fixture_with_meta):
        """혼재 anchor('Day 1'·'Visit 1'·절대날짜) → inconsistent=False, fail→Q02 (naive presence-pass 차단)."""
        df, meta, expected = load_fixture_with_meta("c0213", "trap")
        result = verify_time_anchor(df, meta)
        assert result["time_anchor_consistent"] is False
        assert result["pass"] is False
        assert result["route_to_q"] == "Q02"


class TestC0251:
    """c0251 — A3 실패 라우팅 (ROUTE TIME_FORMAT)

    postcondition_predicate:
        routing_decision in ['Q02', 'Q12', 'INVALID']

    srp_intent: ROUTE TIME_FORMAT
    kind: route
    requires_detection_by: c0203
    can_route_to_q: ['Q02', 'Q12']
    매핑(SSOT strands.json + q_codes + GAP-7): AMBIGUOUS→Q02, UNRECOVERABLE→Q12.
    (spec snippet 산문 'UNRECOVERABLE→INVALID'는 무시 — postcond Q12 허용 + 397 strand Q12.)
    """

    def test_happy(self, load_fixture_with_meta):
        """a3_state=AMBIGUOUS → Q02 (terminal QUARANTINE)."""
        df, meta, expected = load_fixture_with_meta("c0251", "happy")
        result = route_time_format(df, meta)
        assert result["routing_decision"] in ['Q02', 'Q12', 'INVALID']
        assert result["routing_decision"] == expected["routing_decision"]
        assert result["terminal"] == expected["terminal"]
        assert result["q_code"] == expected["q_code"]

    def test_edge(self, load_fixture_with_meta):
        """a3_state=UNRECOVERABLE → Q12 (snippet 'INVALID' 산문 무시; SSOT/GAP-7)."""
        df, meta, expected = load_fixture_with_meta("c0251", "edge")
        result = route_time_format(df, meta)
        assert result["routing_decision"] in ['Q02', 'Q12', 'INVALID']
        assert result["routing_decision"] == expected["routing_decision"]
        assert result["q_code"] == expected["q_code"]

    def test_trap(self, load_fixture_with_meta):
        """★ snippet-literal 차단: UNRECOVERABLE을 INVALID로 silent 라우팅 금지 → Q12 (can_route_to_q·strands SSOT)."""
        df, meta, expected = load_fixture_with_meta("c0251", "trap")
        result = route_time_format(df, meta)
        assert result["routing_decision"] != "INVALID"
        assert result["routing_decision"] == "Q12"
        assert result["q_code"] == "Q12"


class TestC0310:
    """c0310 — 시간 형식 감지 (DETECT TIME_FORMAT)

    postcondition_predicate:
        meta.get('time_format_detected') in ['clock','elapsed','decimal','datetime','mixed']

    srp_intent: DETECT TIME_FORMAT
    kind: detect
    requires_detection_by: null
    can_route_to_q: []
    verify_visualization:
        pass_route_to: c0311
        fail_route_to: null
    (함수명 detect_time_format_mess — c0203 detect_time_format(L-3->L-4 축)와 구분.)
    """

    def test_happy(self, load_fixture_with_meta):
        """clock 표기([0:00,1:30,3:00]) → time_format_detected='clock', pass→c0311."""
        df, meta, expected = load_fixture_with_meta("c0310", "happy")
        result = detect_time_format_mess(df, meta)
        assert result["time_format_detected"] == expected["time_format_detected"]
        assert result["pass"] == expected["pass"]
        assert result["route_to_q"] == expected["route_to_q"]
        assert meta.get('time_format_detected') in ['clock', 'elapsed', 'decimal', 'datetime', 'mixed']

    def test_edge(self, load_fixture_with_meta):
        """순수 numeric([0,1.5,3]) → 'decimal'."""
        df, meta, expected = load_fixture_with_meta("c0310", "edge")
        result = detect_time_format_mess(df, meta)
        assert result["time_format_detected"] == expected["time_format_detected"]
        assert meta.get('time_format_detected') in ['clock', 'elapsed', 'decimal', 'datetime', 'mixed']

    def test_trap(self, load_fixture_with_meta):
        """혼재(clock+decimal+datetime) → 'mixed' (naive 첫값-추정 'clock' silent 차단)."""
        df, meta, expected = load_fixture_with_meta("c0310", "trap")
        result = detect_time_format_mess(df, meta)
        assert result["time_format_detected"] == "mixed"
        assert meta.get('time_format_detected') in ['clock', 'elapsed', 'decimal', 'datetime', 'mixed']


class TestC0314:
    """c0314 — 시간 기준점 감지 (DETECT TIME_ANCHOR)

    postcondition_predicate:
        meta.get('time_anchor_type') is not None

    srp_intent: DETECT TIME_ANCHOR
    kind: detect
    requires_detection_by: null
    can_route_to_q: []
    verify_visualization:
        pass_route_to: c0315
        fail_route_to: null
    """

    def test_happy(self, load_fixture_with_meta):
        """단일 유형 anchor([Day 1,Day 2,Day 3]) → 'day-relative', pass→c0315."""
        df, meta, expected = load_fixture_with_meta("c0314", "happy")
        result = detect_time_anchor(df, meta)
        assert result["time_anchor_type"] == expected["time_anchor_type"]
        assert result["pass"] == expected["pass"]
        assert result["route_to_q"] == expected["route_to_q"]
        assert meta.get('time_anchor_type') is not None

    def test_edge(self, load_fixture_with_meta):
        """anchor 토큰 부재 → 'none'(None 아님; postcond 충족, 날조 없이 부재 표기)."""
        df, meta, expected = load_fixture_with_meta("c0314", "edge")
        result = detect_time_anchor(df, meta)
        assert result["time_anchor_type"] == expected["time_anchor_type"]
        assert meta.get('time_anchor_type') is not None

    def test_trap(self, load_fixture_with_meta):
        """혼재 anchor([Day 1,Day 2,절대날짜]) → 'mixed' (단일유형 silent 오판 차단); 절대 None 금지."""
        df, meta, expected = load_fixture_with_meta("c0314", "trap")
        result = detect_time_anchor(df, meta)
        assert result["time_anchor_type"] == "mixed"
        assert meta.get('time_anchor_type') is not None


class TestC0311:
    """c0311 — 시간 형식 변환 (CONVERT TIME_FORMAT)

    postcondition_predicate:
        df['time_value'].apply(lambda x: isinstance(x, (int, float))).all()

    srp_intent: CONVERT TIME_FORMAT
    kind: transform
    requires_detection_by: c0310
    can_route_to_q: ['Q02']
    """

    def test_happy(self, load_fixture_with_meta):
        """clock [0:00,1:30,3:00] → numeric [0.0,1.5,3.0] (elapsed hours)."""
        df, meta, expected = load_fixture_with_meta("c0311", "happy")
        result = convert_time_format(df, meta)
        assert result["success"] == expected["success"]
        df_out = result["df"]
        assert df_out['time_value'].apply(lambda x: isinstance(x, (int, float))).all()
        assert list(df_out["time_value"]) == expected["time_value"]

    def test_edge(self, load_fixture_with_meta):
        """이미 numeric(decimal) → 통과(idempotent), 값 보존."""
        df, meta, expected = load_fixture_with_meta("c0311", "edge")
        result = convert_time_format(df, meta)
        assert result["success"] == expected["success"]
        df_out = result["df"]
        assert df_out['time_value'].apply(lambda x: isinstance(x, (int, float))).all()
        assert list(df_out["time_value"]) == expected["time_value"]

    def test_trap(self, load_fixture_with_meta):
        """silent no-op 차단: clock 문자열이 실제 numeric으로 변환(미변환 시 postcond 위반·문자열 잔존)."""
        df, meta, expected = load_fixture_with_meta("c0311", "trap")
        result = convert_time_format(df, meta)
        df_out = result["df"]
        assert df_out['time_value'].apply(lambda x: isinstance(x, (int, float))).all()
        assert not any(isinstance(x, str) for x in df_out["time_value"])
        assert list(df_out["time_value"]) == expected["time_value"]


class TestC0315:
    """c0315 — 시간 기준점 파싱 (CONVERT TIME_ANCHOR)

    postcondition_predicate:
        df.get('time_anchor_parsed', pd.Series()).notna().all() if 'time_anchor_parsed' in df.columns else True

    srp_intent: CONVERT TIME_ANCHOR
    kind: transform
    requires_detection_by: c0314
    can_route_to_q: ['Q02']
    """

    def test_happy(self, load_fixture_with_meta):
        """anchor [Day 1,Day 2,Day 3] → time_anchor_parsed [0,24,48] hours."""
        df, meta, expected = load_fixture_with_meta("c0315", "happy")
        result = convert_time_anchor(df, meta)
        assert result["success"] == expected["success"]
        df_out = result["df"]
        assert df_out.get('time_anchor_parsed', pd.Series()).notna().all() if 'time_anchor_parsed' in df_out.columns else True
        assert list(df_out["time_anchor_parsed"]) == expected["time_anchor_parsed"]

    def test_edge(self, load_fixture_with_meta):
        """time_anchor 컬럼 부재 → 변환 대상 없음, postcond vacuous True, success."""
        df, meta, expected = load_fixture_with_meta("c0315", "edge")
        result = convert_time_anchor(df, meta)
        assert result["success"] == expected["success"]
        df_out = result["df"]
        assert df_out.get('time_anchor_parsed', pd.Series()).notna().all() if 'time_anchor_parsed' in df_out.columns else True

    def test_trap(self, load_fixture_with_meta):
        """vacuous no-op 차단: time_anchor 존재 시 time_anchor_parsed가 실제 생성·정확(부재로 postcond 우회 금지)."""
        df, meta, expected = load_fixture_with_meta("c0315", "trap")
        result = convert_time_anchor(df, meta)
        df_out = result["df"]
        assert "time_anchor_parsed" in df_out.columns
        assert list(df_out["time_anchor_parsed"]) == expected["time_anchor_parsed"]


class TestC0312:
    """c0312 — 시간대 감지 (DETECT TIMEZONE)

    postcondition_predicate:
        isinstance(meta.get('tz_issues'), dict)

    srp_intent: DETECT TIMEZONE
    kind: detect
    requires_detection_by: null
    can_route_to_q: []
    verify_visualization:
        pass_route_to: c0313
        fail_route_to: null
    """

    def test_happy(self, load_fixture_with_meta):
        """혼합 시간대([00:00 UTC, 09:00 KST]) → tz_issues.has_mixed_tz=True, pass→c0313."""
        df, meta, expected = load_fixture_with_meta("c0312", "happy")
        result = detect_timezone(df, meta)
        assert result["tz_issues"] == expected["tz_issues"]
        assert result["pass"] == expected["pass"]
        assert result["route_to_q"] == expected["route_to_q"]
        assert isinstance(meta.get('tz_issues'), dict)

    def test_edge(self, load_fixture_with_meta):
        """단일 시간대([08:00 KST, 09:00 KST]) → has_mixed_tz=False (불일치 없음 정직 표기)."""
        df, meta, expected = load_fixture_with_meta("c0312", "edge")
        result = detect_timezone(df, meta)
        assert result["tz_issues"] == expected["tz_issues"]
        assert isinstance(meta.get('tz_issues'), dict)

    def test_trap(self, load_fixture_with_meta):
        """3종 혼재([KST, JST, UTC]) → n_distinct_tz=3 (naive '모두 동일' silent 오판 차단)."""
        df, meta, expected = load_fixture_with_meta("c0312", "trap")
        result = detect_timezone(df, meta)
        assert result["tz_issues"]["has_mixed_tz"] is True
        assert result["tz_issues"]["n_distinct_tz"] == 3
        assert isinstance(meta.get('tz_issues'), dict)


class TestC0313:
    """c0313 — 시간대 정규화 (NORMALIZE TIMEZONE)

    postcondition_predicate:
        meta.get('tz_normalized', True)

    srp_intent: NORMALIZE TIMEZONE
    kind: transform
    requires_detection_by: c0312
    can_route_to_q: []
    (★ postcond는 default=True라 no-op도 vacuously 통과 — GAP-27. trap/missing-detection test가
     실제 정규화·flag 명시 설정·비-silent failure를 강제한다. c0315 vacuous-postcond 선례 동형.)
    """

    def test_happy(self, load_fixture_with_meta):
        """혼합 tz [00:00 UTC, 09:00 KST] → 단일 target UTC [00:00 UTC, 00:00 UTC]."""
        df, meta, expected = load_fixture_with_meta("c0313", "happy")
        result = normalize_timezone(df, meta)
        assert result["success"] == expected["success"]
        df_out = result["df"]
        assert list(df_out["time_value"]) == expected["time_value"]
        assert meta.get('tz_normalized', True)

    def test_edge(self, load_fixture_with_meta):
        """단일 tz(KST) → idempotent 통과, 값 보존."""
        df, meta, expected = load_fixture_with_meta("c0313", "edge")
        result = normalize_timezone(df, meta)
        assert result["success"] == expected["success"]
        df_out = result["df"]
        assert list(df_out["time_value"]) == expected["time_value"]
        assert meta.get('tz_normalized', True)

    def test_trap(self, load_fixture_with_meta):
        """vacuous/silent no-op 차단: 혼합 tz가 실제 단일 tz로 변환 + flag 명시 설정(미변환 시 잔존 tz·flag 미설정)."""
        df, meta, expected = load_fixture_with_meta("c0313", "trap")
        result = normalize_timezone(df, meta)
        df_out = result["df"]
        assert list(df_out["time_value"]) == expected["time_value"]
        assert {str(v).split()[-1] for v in df_out["time_value"]} == {"UTC"}
        assert meta.get('tz_normalized') is True   # default(True)가 아닌 명시 설정 확인

    def test_tz_issues_missing_not_silent_noop(self):
        """★ GAP-27/GAP-21(C): detection(c0312) 산출물 meta['tz_issues'] 부재 시 silent 통과 금지 —
        success=False·route_to_q=None(Q 날조 금지)·flag 미설정(vacuous postcond에 의존하지 않음)."""
        df = pd.DataFrame({"time_value": ["08:00 KST", "09:00 JST"]})
        meta = {}
        result = normalize_timezone(df, meta)
        assert result["success"] is False
        assert result["route_to_q"] is None
        assert meta.get('tz_normalized') is not True
