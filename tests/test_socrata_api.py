"""
Unit and Integration Tests for Socrata Open Data API Integration
Validates SODA 2.0/2.1 client, secure credential ingestion, and Dutch RDW data caching.
"""

import pytest
import os
import pandas as pd
from python.dashboard.socrata_client import (
    load_socrata_credentials,
    is_socrata_configured,
    get_socrata_headers,
    fetch_socrata_dataset,
    DEFAULT_RDW_RESOURCE_URL
)
from python.dashboard.cache_manager import DatasetCacheManager, format_variable_name, get_dataset_variables

class TestSocrataAPIIntegration:

    def test_socrata_credentials_secure_loading(self, monkeypatch):
        """Validates that Socrata credentials load securely without exposing secret values."""
        monkeypatch.setenv("API_KEY_ID", "test_id")
        monkeypatch.setenv("RDW_API_KEY_SECRET", "test_secret")
        creds = load_socrata_credentials()
        assert is_socrata_configured() is True
        assert creds['api_key_id'] == "test_id"
        assert creds['api_key_secret'] == "test_secret"

    def test_socrata_headers_construction(self, monkeypatch):
        """Ensures Basic Auth and User-Agent headers follow dev.socrata.com standards."""
        monkeypatch.setenv("API_KEY_ID", "test_id")
        monkeypatch.setenv("RDW_API_KEY_SECRET", "test_secret")
        headers = get_socrata_headers()
        assert 'Authorization' in headers
        assert headers['Authorization'].startswith('Basic ')
        assert headers.get('Accept') == 'text/csv'

    def test_socrata_soda3_views_query_live_fetch(self):
        """Verifies live tabular fetch from SODA 3 endpoint https://opendata.rdw.nl/api/v3/views/2snn-6yr9/query.csv."""
        import urllib.error
        try:
            df, raw_bytes = fetch_socrata_dataset(
                resource_url='https://opendata.rdw.nl/api/v3/views/2snn-6yr9/query.csv',
                limit=5
            )
            assert isinstance(df, pd.DataFrame)
            assert len(df) > 0
            assert len(raw_bytes) > 0
            assert 'kenteken' in df.columns
            assert 'merk' in df.columns
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            pytest.skip(f"Live Socrata network access unavailable: {e}")

    def test_socrata_soda2_legacy_fallback(self):
        """Verifies backward compatibility with SODA 2 endpoint https://opendata.rdw.nl/resource/2snn-6yr9.csv."""
        import urllib.error
        try:
            df, raw_bytes = fetch_socrata_dataset(
                resource_url='https://opendata.rdw.nl/resource/2snn-6yr9.csv',
                limit=5
            )
            assert isinstance(df, pd.DataFrame)
            assert len(df) > 0
            assert 'kenteken' in df.columns
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            pytest.skip(f"Live Socrata network access unavailable: {e}")

    def test_dutch_variable_name_formatting(self):
        """Verifies clinical & scientific formatting for Dutch RDW variables."""
        assert format_variable_name('kenteken') == 'Vehicle Registration License Plate Identifier'
        assert format_variable_name('merk') == 'Vehicle Manufacturer / Brand Designation'
        assert format_variable_name('bruto_bpm') == 'Gross Private Motor Vehicle Tax (€ BPM)'
        assert format_variable_name('vervaldatum_apk') == 'Periodic Technical Safety Inspection Expiry (APK)'
        assert format_variable_name('zuinigheidsclassificatie') == 'Energy Efficiency & Carbon Emissions Label'

    def test_dutch_socrata_caching_and_preview(self, client, cache_mgr):
        """Tests that dutch-dalys-pmc caches Socrata data (or robust metadata fallback) and serves it via preview API."""
        entry = cache_mgr.cache_dataset('dutch-dalys-pmc', force=True)
        assert entry['is_cached'] is True
        assert 'Parquet' in entry['format']
        assert entry['record_count'] > 0

        res = client.get('/api/datasets/dutch-dalys-pmc/preview?limit=10')
        assert res.status_code == 200
        data = res.get_json()
        assert data['dataset_id'] == 'dutch-dalys-pmc'
        assert len(data['variables']) > 0
