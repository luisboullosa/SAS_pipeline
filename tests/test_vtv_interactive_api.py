"""
Unit and Integration Tests for Dutch PHFS / VTV Interactive Subsetting & Reporting API.
Validates:
- GET /api/vtv/diseases (Nomenclature, 16 conditions, category sorting)
- GET/POST /api/vtv/years (2020-2023 observed and 2030-2050 trend horizons)
- GET/POST /api/vtv/strata (Demographics, Age strata, Metrics)
- POST /api/vtv/report (Multi-page Nature, Ecology, Sapphire publication PDF reports)
- Integrated POST /api/report with dataset='cbs-vtv-phfs'
"""

import os
import pytest
import pypdf

class TestVTVInteractiveAPI:

    def test_vtv_diseases_endpoint(self, client):
        res = client.get('/api/vtv/diseases')
        assert res.status_code == 200
        data = res.get_json()
        assert isinstance(data, list)
        assert len(data) >= 16, "Must provide at least 16 VTV conditions plus ALL aggregate"

        codes = [d['code'] for d in data]
        assert 'ALL' in codes
        assert codes[0] == 'ALL', "ALL aggregate must be first option"
        assert 'Respiratory & Pulmonary Diseases' in codes
        assert 'Musculoskeletal & Joint Diseases' in codes
        assert 'Mental & Behavioral Disorders' in codes
        assert 'All Cancers & Neoplasms' in codes

        # Verify each item has 'code', 'name', 'category'
        for item in data:
            assert 'code' in item
            assert 'name' in item
            assert 'category' in item

    def test_vtv_years_endpoint(self, client):
        res = client.get('/api/vtv/years')
        assert res.status_code == 200
        years = res.get_json()
        assert isinstance(years, list)
        
        year_codes = [y['code'] for y in years]
        assert 'ALL' in year_codes
        assert '2020' in year_codes
        assert '2022' in year_codes
        assert '2030' in year_codes
        assert '2050' in year_codes

    def test_vtv_strata_endpoint(self, client):
        res = client.get('/api/vtv/strata')
        assert res.status_code == 200
        data = res.get_json()
        assert 'genders' in data
        assert 'age_strata' in data
        assert 'metrics' in data

        gender_codes = [g['code'] for g in data['genders']]
        assert 'Both Sexes' in gender_codes
        assert 'Male' in gender_codes
        assert 'Female' in gender_codes

        age_codes = [a['code'] for a in data['age_strata']]
        assert 'ALL' in age_codes
        assert '65-74' in age_codes
        assert '75+' in age_codes

        metric_codes = [m['code'] for m in data['metrics']]
        assert 'DALY' in metric_codes
        assert 'YLL' in metric_codes
        assert 'YLD' in metric_codes

    def test_vtv_report_generation_endpoint(self, client):
        payload = {
            'diseases': ['Musculoskeletal & Joint Diseases', 'Mental & Behavioral Disorders'],
            'years': ['2021', '2022'],
            'gender': 'Both Sexes',
            'age_strata': ['65-74', '75+'],
            'metric': 'DALY',
            'style': 'nature'
        }
        res = client.post('/api/vtv/report', json=payload)
        assert res.status_code == 200
        data = res.get_json()
        assert 'report_url' in data
        assert data['report_url'].endswith('.pdf')

        # Verify generated PDF file structure
        filename = data['report_url'].split('/')[-1]
        pdf_path = os.path.join(os.path.dirname(__file__), '..', 'python', 'dashboard', 'static', 'reports', filename)
        assert os.path.exists(pdf_path)

        reader = pypdf.PdfReader(pdf_path)
        assert len(reader.pages) >= 3, "VTV report must contain at least 3 pages (Trajectory, Comparison, Tables)"
        
        all_text = " ".join([p.extract_text() for p in reader.pages])
        assert "Figure 1" in all_text
        assert "Figure 2" in all_text
        assert "Table 1" in all_text
        assert "Table 2" in all_text
        assert "Table 3" in all_text
        assert "Executive Summary Table" in all_text
        assert "DALY" in all_text

    def test_vtv_report_routed_via_generic_report_endpoint(self, client):
        payload = {
            'dataset': 'cbs-vtv-phfs',
            'diseases': ['ALL'],
            'years': ['ALL'],
            'gender': 'Female',
            'age_strata': ['ALL'],
            'metric': 'YLL',
            'style': 'ecology'
        }
        res = client.post('/api/report', json=payload)
        assert res.status_code == 200
        data = res.get_json()
        assert 'report_url' in data
        assert 'report_vtv_' in data['report_url']
