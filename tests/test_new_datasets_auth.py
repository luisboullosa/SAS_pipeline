"""
Tests for Zenodo API Token Authentication & Newly Connected Open Datasets:
- CBS VTV Lifestyle & Determinants Monitor (85464NED)
- CBS Population Forecast 2022-2070 (85323NED)
- WHO Global Health Observatory Benchmarks (who-gho-odata)
"""

import os
import pytest
import pandas as pd
from python.dashboard.socrata_client import (
    load_zenodo_credentials,
    is_zenodo_configured,
    get_zenodo_headers
)
from python.dashboard.cache_manager import DatasetCacheManager, format_variable_name

class TestNewDatasetsAndAuth:

    def test_zenodo_credentials_secure_loading(self, monkeypatch):
        """Validates that Zenodo API token loads securely without exposing its value."""
        monkeypatch.setenv("ZENODO_API_TOKEN", "mock_zenodo_token")
        creds = load_zenodo_credentials()
        assert is_zenodo_configured() is True
        token = creds.get('zenodo_token')
        assert token == "mock_zenodo_token"
        # Verify headers
        headers = get_zenodo_headers()
        assert 'Authorization' in headers
        assert headers['Authorization'] == "Bearer mock_zenodo_token"

    def test_cbs_vtv_determinants_caching_and_preview(self):
        """Verifies caching and preview for CBS Lifestyle & Determinants Monitor."""
        cm = DatasetCacheManager()
        info = cm.cache_dataset('cbs-vtv-determinants', force=False)
        assert info['record_count'] > 0
        assert os.path.exists(info['parquet_path'])

        df = cm.load_dataframe('cbs-vtv-determinants')
        assert not df.empty
        assert 'Rokers_1' in df.columns or 'Drinkers_6' in df.columns

        # Verify variable formatting
        vars_meta = cm.get_dataset_variables(df)
        var_names = [v['formatted_name'] for v in vars_meta]
        assert any('Smoking' in n or 'Rokers' in n for n in var_names)

    def test_cbs_population_forecast_caching_and_preview(self):
        """Verifies caching and preview for CBS Population Forecast 2022-2070."""
        cm = DatasetCacheManager()
        info = cm.cache_dataset('cbs-population-forecast', force=False)
        assert info['record_count'] > 0
        assert os.path.exists(info['parquet_path'])

        df = cm.load_dataframe('cbs-population-forecast')
        assert not df.empty
        assert 'BevolkingOp1Januari_1' in df.columns or 'PrognoseInterval' in df.columns

        vars_meta = cm.get_dataset_variables(df)
        assert len(vars_meta) >= 10

    def test_who_gho_odata_caching_and_preview(self):
        """Verifies caching and preview for WHO Global Health Observatory benchmarks."""
        cm = DatasetCacheManager()
        info = cm.cache_dataset('who-gho-odata', force=False)
        assert info['record_count'] > 0
        assert os.path.exists(info['parquet_path'])

        df = cm.load_dataframe('who-gho-odata')
        assert not df.empty
        assert 'Country_Code' in df.columns
        assert 'Life_Expectancy' in df.columns

    def test_preview_endpoints_in_api(self, client):
        """Tests that preview API returns rows and variable metadata for the new datasets."""
        for ds_id in ['cbs-vtv-determinants', 'cbs-population-forecast', 'who-gho-odata']:
            res = client.get(f'/api/datasets/{ds_id}/preview?limit=5')
            assert res.status_code == 200
            data = res.get_json()
            assert data['dataset_id'] == ds_id
            assert len(data['rows']) > 0
            assert len(data['variables']) > 0
            assert data['variables_count'] > 0
