"""
Comprehensive Test Suite for Dataset & Sets-of-Datasets Caching Engine
Validates Parquet columnar storage, fast load performance, dataset sets/bundles,
manifest persistence, and REST API cache endpoints.
"""

import os
import pytest
from python.dashboard.app import app
from python.dashboard.cache_manager import DatasetCacheManager, DATASET_SETS

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

@pytest.fixture
def cache_mgr():
    return DatasetCacheManager()

class TestDatasetCaching:

    def test_cache_manager_initialization(self, cache_mgr):
        assert os.path.exists(cache_mgr.cache_dir)
        assert os.path.exists(cache_mgr.manifest_file)
        manifest = cache_mgr._read_manifest()
        assert 'datasets' in manifest

    def test_cache_ecdc_primary_dataset(self, cache_mgr):
        # Cache the primary dataset
        entry = cache_mgr.cache_dataset('ecdc-covid-vaccine', force=False)
        assert entry['is_cached'] is True
        assert entry['dataset_id'] == 'ecdc-covid-vaccine'
        assert entry['record_count'] == 813367
        assert entry['parquet_size_mb'] > 0
        assert os.path.exists(entry['parquet_path'])
        assert 'YearWeekISO' in entry['columns']
        assert 'ReportingCountry' in entry['columns']

    def test_fast_parquet_dataframe_loading(self, cache_mgr):
        df = cache_mgr.load_dataframe('ecdc-covid-vaccine')
        assert df is not None
        assert len(df) == 813367
        assert 'TargetGroup' in df.columns

    def test_dataset_sets_definition(self):
        assert 'all' in DATASET_SETS
        assert 'epidemiology' in DATASET_SETS
        assert 'environmental_ecology' in DATASET_SETS
        assert 'neuro_behavioral' in DATASET_SETS

        assert len(DATASET_SETS['all']['datasets']) == 16
        assert 'ecdc-covid-vaccine' in DATASET_SETS['epidemiology']['datasets']
        assert 'cbs-vtv-phfs' in DATASET_SETS['epidemiology']['datasets']
        assert 'cbs-vtv-determinants' in DATASET_SETS['epidemiology']['datasets']
        assert 'cbs-population-forecast' in DATASET_SETS['epidemiology']['datasets']
        assert 'who-gho-odata' in DATASET_SETS['epidemiology']['datasets']
        assert 'foto-nl-water-pollution' in DATASET_SETS['environmental_ecology']['datasets']
        assert 'sa-fari-wildlife' in DATASET_SETS['environmental_ecology']['datasets']
        assert 'mendeley-neurodiversity' in DATASET_SETS['neuro_behavioral']['datasets']

    def test_cache_dataset_set_batch(self, cache_mgr):
        # Cache the epidemiology set
        res = cache_mgr.cache_set('epidemiology', force=False)
        assert res['set_id'] == 'epidemiology'
        assert res['total_in_set'] == 7
        assert len(res['results']) == 7
        for r in res['results']:
            assert r['status'] == 'success'

        summary = cache_mgr.get_cache_summary()
        assert summary['sets']['epidemiology']['is_fully_cached'] is True

    def test_api_cache_manifest_endpoint(self, client):
        response = client.get('/api/cache')
        assert response.status_code == 200
        data = response.get_json()
        assert 'total_cached_datasets' in data
        assert 'total_parquet_mb' in data
        assert 'sets' in data
        assert data['total_cached_datasets'] >= 1

    def test_api_cache_sets_endpoint(self, client):
        response = client.get('/api/cache/sets')
        assert response.status_code == 200
        data = response.get_json()
        assert 'epidemiology' in data
        assert 'environmental_ecology' in data
        assert 'neuro_behavioral' in data
        assert 'all' in data

    def test_api_cache_refresh_set(self, client):
        response = client.post('/api/cache/refresh', json={'set_id': 'neuro_behavioral'})
        assert response.status_code == 200
        data = response.get_json()
        assert data['set_id'] == 'neuro_behavioral'
        assert data['total_in_set'] == 4
        for r in data['results']:
            assert r['status'] == 'success'

    def test_api_cache_refresh_single_dataset(self, client):
        response = client.post('/api/cache/refresh', json={'dataset_id': 'ecdc-covid-vaccine'})
        assert response.status_code == 200
        data = response.get_json()
        assert data['dataset_id'] == 'ecdc-covid-vaccine'
        assert data['is_cached'] is True

    def test_api_datasets_enriched_with_cache_info(self, client):
        response = client.get('/api/datasets')
        assert response.status_code == 200
        datasets = response.get_json()
        ecdc = next(d for d in datasets if d['id'] == 'ecdc-covid-vaccine')
        assert ecdc['is_cached'] is True
        assert ecdc['cache_info'] is not None
        assert ecdc['cache_info']['record_count'] == 813367

    def test_cache_clear_and_rebuild(self, client, cache_mgr):
        # Clear a single dataset
        del_resp = client.post('/api/cache/clear', json={'dataset_id': 'liss-panel-nl'})
        assert del_resp.status_code == 200
        assert cache_mgr.is_cached('liss-panel-nl') is False

        # Re-cache
        recache_resp = client.post('/api/cache/refresh', json={'dataset_id': 'liss-panel-nl'})
        assert recache_resp.status_code == 200
        assert cache_mgr.is_cached('liss-panel-nl') is True

    def test_zip_package_unzipping_and_member_discovery(self, cache_mgr):
        entry = cache_mgr.cache_dataset('unep-gems-water', force=True)
        assert entry['is_package'] is True
        assert entry['package_members_count'] >= 3

        members = cache_mgr.get_package_members('unep-gems-water')
        assert len(members) >= 3
        member_files = [m['file_name'] for m in members]
        assert 'GEMStat_station_metadata.csv' in member_files
        assert 'GEMStat_parameter_metadata.csv' in member_files

        df_member = cache_mgr.load_member_dataframe('unep-gems-water', 'GEMStat_station_metadata.csv')
        assert df_member is not None
        assert 'station_id' in df_member.columns

    def test_variable_formatting_and_citations(self, cache_mgr):
        from python.dashboard.cache_manager import format_variable_name, get_dataset_variables
        import pandas as pd

        assert format_variable_name('YearWeekISO') == 'Calendar Year & Week (ISO 8601)'
        assert format_variable_name('station_id') == 'Hydrological Monitoring Station ID'
        assert format_variable_name('species_id') == 'Taxonomic Species Identifier'
        assert format_variable_name('custom_test_variable') == 'Custom Test Variable'

        test_df = pd.DataFrame({
            'YearWeekISO': ['2021-W01'],
            'ReportingCountry': ['FR'],
            'Denominator': [1000000]
        })
        vars_meta = get_dataset_variables(test_df)
        assert len(vars_meta) == 3
        assert vars_meta[0]['number'] == 1
        assert vars_meta[0]['var_number'] == 'Var #1'
        assert vars_meta[0]['raw_name'] == 'YearWeekISO'
        assert vars_meta[0]['formatted_name'] == 'Calendar Year & Week (ISO 8601)'
        assert 'Variables Cited (N=3)' in f"Variables Cited (N={len(vars_meta)})"
