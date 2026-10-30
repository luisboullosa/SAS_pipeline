"""
Unit and Integration Tests for Dutch Public Health Foresight Study (VTV/PHFS) Project
Validates CBS OData (cbsodata) client, DALY calculation pipeline, and dashboard integration.
Reference: Hilderink et al., Eur J Public Health 2025 (doi: 10.1093/eurpub/ckaf161.580).
"""

import os
import sys
import pytest
import pandas as pd

PROJECT_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "projects", "dutch_phfs_burden_of_disease")
)
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

from cbs_client import CBSVTVClient, VTV_DISEASE_MAP
from vtv_daly_pipeline import VTVDALYPipeline

class TestDutchPHFSProject:

    def test_cbs_vtv_client_local_cache_read(self):
        """Verifies that CBSVTVClient loads cached morbidity data from Parquet."""
        client = CBSVTVClient(cache_dir=os.path.join(PROJECT_DIR, "data"))
        df = client.fetch_vtv_hospital_morbidity(years=["2023"])
        assert isinstance(df, pd.DataFrame)
        assert len(df) > 0
        assert "DiagnoseIndelingVTV" in df.columns
        assert "Opnamen_1" in df.columns

    def test_vtv_disease_taxonomy_mapping(self):
        """Ensures key public health priority diseases are mapped properly."""
        assert "2 Totaal nieuwvormingen" in VTV_DISEASE_MAP
        assert "9 Totaal zkt. van hart- en vaatstelsel" in VTV_DISEASE_MAP
        assert "5.7.1 Depressieve stoornissen" in VTV_DISEASE_MAP
        assert "21 Totaal COVID-19" in VTV_DISEASE_MAP

    def test_vtv_daly_pipeline_execution_and_math(self):
        """Validates that DALY pipeline correctly calculates DALY = YLL + YLD."""
        pipeline = VTVDALYPipeline(data_dir=os.path.join(PROJECT_DIR, "data"))
        agg_morb, summary_df = pipeline.run_pipeline(years=["2023"])
        
        assert len(agg_morb) > 0
        assert len(summary_df) > 0
        
        # Verify mathematical identity: DALY = YLL + YLD
        for _, row in agg_morb.head(50).iterrows():
            expected_daly = row["YLL"] + row["YLD"]
            assert abs(row["DALY"] - expected_daly) < 1e-4
            assert row["DALY_Rate_Per10k"] >= 0
            assert 0.0 <= row["YLL_Pct"] <= 100.01

        # Check top ranking condition (Neoplasms should rank #1 per Dutch Burden Study)
        top_disease = summary_df.iloc[0]["Disease_Name"]
        assert "Cancer" in top_disease or "Neoplasm" in top_disease

    def test_sas_templates_and_macros_exist(self):
        """Verifies that SAS macro and report generation files exist."""
        macro_file = os.path.join(PROJECT_DIR, "sas", "daly_macro.sas")
        report_file = os.path.join(PROJECT_DIR, "sas", "phfs_nature_report.sas")
        assert os.path.exists(macro_file)
        assert os.path.exists(report_file)

    def test_dashboard_preview_endpoint_for_cbs_vtv(self, client, cache_mgr):
        """Verifies that cbs-vtv-phfs can be cached and explored via preview API."""
        entry = cache_mgr.cache_dataset("cbs-vtv-phfs", force=True)
        assert entry["is_cached"] is True
        assert "DALY" in entry["columns"]
        assert "Disease_Name" in entry["columns"]
        assert entry["record_count"] > 0

        res = client.get("/api/datasets/cbs-vtv-phfs/preview?limit=10")
        assert res.status_code == 200
        data = res.get_json()
        assert data["dataset_id"] == "cbs-vtv-phfs"
        assert "DALY" in data["columns"]
        assert len(data["rows"]) > 0
        
        # Verify variable codebook enrichment
        var_names = [v["raw_name"] for v in data["variables"]]
        assert "DALY" in var_names
        assert "YLL" in var_names
        assert "YLD" in var_names
