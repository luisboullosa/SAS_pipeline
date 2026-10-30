import os
import sys
import pytest

os.environ['TESTING'] = '1'

# Ensure python and python/dashboard are on the python path
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DASHBOARD_DIR = os.path.join(ROOT_DIR, 'python', 'dashboard')
PYTHON_DIR = os.path.join(ROOT_DIR, 'python')

for p in [ROOT_DIR, PYTHON_DIR, DASHBOARD_DIR]:
    if p not in sys.path:
        sys.path.insert(0, p)

from app import app, get_recent_reports_list, COUNTRY_MAP, AGE_MAP

@pytest.fixture(scope='session')
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

@pytest.fixture
def cache_mgr():
    from cache_manager import DatasetCacheManager
    return DatasetCacheManager()
