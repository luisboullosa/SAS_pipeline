import pytest
import json
from app import COUNTRY_MAP, AGE_MAP

class TestDashboardAPI:

    def test_datasets_endpoint(self, client):
        response = client.get('/api/datasets')
        assert response.status_code == 200
        data = response.get_json()
        assert isinstance(data, list)
        assert len(data) >= 11, "Catalogue must contain at least 11 datasets"

        for d in data:
            for field in ['id', 'name', 'provider', 'category', 'url', 'description', 'status']:
                assert field in d, f"Dataset {d.get('name')} missing field {field}"

        active = [d for d in data if d['status'] == 'active']
        assert len(active) == 1
        assert active[0]['id'] == 'ecdc-covid-vaccine'

        ids = [d['id'] for d in data]
        assert 'foto-nl-water-pollution' in ids
        assert 'unep-gems-water' in ids
        assert 'dutch-dalys-pmc' in ids
        assert 'health-ri-catalogue' in ids
        assert 'icp-im-air-pollution' in ids
        assert 'loobos-flux-meteorology' in ids
        assert 'mendeley-neurodiversity' in ids
        assert 'edinburgh-share-mh' in ids
        assert 'liss-panel-nl' in ids
        assert 'openneuroscience-ntr' in ids
        assert 'sa-fari-wildlife' in ids
        assert 'cbs-vtv-phfs' in ids
        assert 'cbs-vtv-determinants' in ids
        assert 'cbs-population-forecast' in ids
        assert 'who-gho-odata' in ids

    def test_countries_endpoint(self, client):
        response = client.get('/api/countries')
        assert response.status_code == 200
        data = response.get_json()
        assert isinstance(data, list)
        assert len(data) > 0
        
        # Check structure: 'code' and 'name'
        first = data[0]
        assert 'code' in first
        assert 'name' in first
        
        # Verify alphabetical sorting by country name
        names = [c['name'] for c in data]
        assert names == sorted(names), "Countries list must be sorted alphabetically by display name"

    def test_years_endpoint_get_and_post(self, client):
        # GET request with single country
        res_get = client.get('/api/years?country=FR')
        assert res_get.status_code == 200
        years_get = res_get.get_json()
        assert isinstance(years_get, list)
        assert len(years_get) > 0
        assert '2021' in years_get

        # POST request with multiple countries
        res_post = client.post('/api/years', json={'countries': ['FR', 'DE']})
        assert res_post.status_code == 200
        years_post = res_post.get_json()
        assert isinstance(years_post, list)
        assert len(years_post) > 0

        # POST request with 'ALL'
        res_all = client.post('/api/years', json={'countries': ['ALL']})
        assert res_all.status_code == 200
        years_all = res_all.get_json()
        assert isinstance(years_all, list)
        assert len(years_all) >= len(years_get)

    def test_age_groups_endpoint_and_labels(self, client):
        res = client.post('/api/age_groups', json={'countries': ['FR'], 'years': ['2021']})
        assert res.status_code == 200
        data = res.get_json()
        assert isinstance(data, list)
        assert len(data) > 0

        # Spec: ALL group must be the first item
        assert data[0]['code'] == 'ALL', "ALL group must be the first entry in age groups"
        assert 'All Ages' in data[0]['name']

        # Spec: All age bracket labels must include 'years old'
        for item in data:
            code = item['code']
            name = item['name']
            if code.startswith('Age') and code != 'AgeUNK':
                assert 'years old' in name, f"Age group label for {code} must include 'years old', got: {name}"

    def test_recent_reports_endpoint(self, client):
        response = client.get('/api/recent_reports')
        assert response.status_code == 200
        reports = response.get_json()
        assert isinstance(reports, list)

        if len(reports) > 0:
            first = reports[0]
            assert 'filename' in first
            assert 'title' in first
            assert 'url' in first
            assert 'timestamp' in first
            assert 'date_formatted' in first
            assert 'size_kb' in first
            
            # Spec: Must be ordered in descending order of modification time
            timestamps = [r['timestamp'] for r in reports]
            assert timestamps == sorted(timestamps, reverse=True), "Recent reports must be sorted descending by timestamp"

    def test_report_generation_endpoint(self, client):
        # Generate a test report
        payload = {
            'countries': ['FR'],
            'years': ['2021'],
            'ages': ['Age18_24']
        }
        res = client.post('/api/report', json=payload)
        assert res.status_code == 200
        data = res.get_json()
        assert 'report_url' in data
        assert data['report_url'].endswith('.pdf')

    def test_report_generation_with_publication_styles(self, client):
        # Test Nature Journal style
        payload_nature = {
            'countries': ['FR'],
            'years': ['2021'],
            'ages': ['Age18_24'],
            'style': 'nature'
        }
        res_nature = client.post('/api/report', json=payload_nature)
        assert res_nature.status_code == 200
        data_nature = res_nature.get_json()
        assert 'report_url' in data_nature
        assert data_nature['report_url'].endswith('.pdf')

        # Test Ecology Journal style
        payload_eco = {
            'countries': ['FR'],
            'years': ['2021'],
            'ages': ['Age18_24'],
            'style': 'ecology'
        }
        res_eco = client.post('/api/report', json=payload_eco)
        assert res_eco.status_code == 200
        data_eco = res_eco.get_json()
        assert 'report_url' in data_eco
        assert '_ecology.pdf' in data_eco['report_url']

    def test_dataset_preview_endpoint(self, client):
        # 1. Primary dataset preview with formatted variables and citations
        res = client.get('/api/datasets/ecdc-covid-vaccine/preview?limit=10')
        assert res.status_code == 200
        data = res.get_json()
        assert data['dataset_id'] == 'ecdc-covid-vaccine'
        assert data['total_rows'] == 813367
        assert len(data['rows']) == 10
        assert 'YearWeekISO' in data['columns']
        assert 'ReportingCountry' in data['columns']
        assert 'FirstDose' in data['columns']

        # Verify variables number and formatted names citation
        assert 'variables' in data
        assert len(data['variables']) == len(data['columns'])
        assert data['variables'][0]['number'] == 1
        assert data['variables'][0]['var_number'] == 'Var #1'
        assert data['variables'][0]['raw_name'] == 'YearWeekISO'
        assert data['variables'][0]['formatted_name'] == 'Calendar Year & Week (ISO 8601)'
        assert 'variables_citation_text' in data
        assert 'Variables Cited (N=18): [1] YearWeekISO' in data['variables_citation_text']

        # 2. Filter query search
        res_filter = client.get('/api/datasets/ecdc-covid-vaccine/preview?limit=10&q=2021-W01')
        assert res_filter.status_code == 200
        filter_data = res_filter.get_json()
        assert filter_data['total_filtered'] < filter_data['total_rows']
        assert filter_data['total_filtered'] > 0

        # 3. Zip package unzipping & member dataset exploration (UNEP GEMS/Water)
        res_unep = client.get('/api/datasets/unep-gems-water/preview')
        assert res_unep.status_code == 200
        unep_data = res_unep.get_json()
        assert unep_data['dataset_id'] == 'unep-gems-water'
        assert unep_data['is_package'] is True
        assert len(unep_data['package_members']) >= 3
        # Switch to station metadata member table
        res_station = client.get('/api/datasets/unep-gems-water/preview?member=GEMStat_station_metadata.csv')
        assert res_station.status_code == 200
        station_data = res_station.get_json()
        assert 'station_id' in station_data['columns']
        assert station_data['variables'][0]['formatted_name'] == 'Hydrological Monitoring Station ID'

        # 4. SA-FARI Wildlife Video Dataset exploration
        res_safari = client.get('/api/datasets/sa-fari-wildlife/preview')
        assert res_safari.status_code == 200
        safari_data = res_safari.get_json()
        assert safari_data['dataset_id'] == 'sa-fari-wildlife'
        assert safari_data['is_package'] is True
        assert any('sa_fari_species_catalog.csv' in m['file_name'] for m in safari_data['package_members'])

        # 5. Non-existent dataset
        res_404 = client.get('/api/datasets/non-existent-dataset-id/preview')
        assert res_404.status_code == 404
