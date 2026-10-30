"""
Socrata Open Data API (SODA 3 / SODA 2) Client
Integrates with https://dev.socrata.com/ using SODA 3 Views Query API standards:
https://opendata.rdw.nl/api/v3/views/{resource_id}/query.csv
Safely loads authentication credentials (API_KEY_ID & RDW_API_KEY_SECRET)
without exposing secrets in logs or code.
"""

import os
import io
import json
import base64
import urllib.request
import urllib.parse
from typing import Optional, Dict, Tuple, Any
import pandas as pd

DEFAULT_SECRETS_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..', '..', '.secrets', '.auth.txt')
)
DEFAULT_RDW_RESOURCE_URL = "https://opendata.rdw.nl/api/v3/views/2snn-6yr9/query.csv"
SODA2_LEGACY_RESOURCE_URL = "https://opendata.rdw.nl/resource/2snn-6yr9.csv"

def load_socrata_credentials(secrets_path: Optional[str] = None) -> Dict[str, Optional[str]]:
    """
    Safely retrieves Socrata API credentials from secrets file or environment variables.
    Never logs or echoes secret values.
    """
    key_id: Optional[str] = os.environ.get('API_KEY_ID')
    key_secret: Optional[str] = os.environ.get('RDW_API_KEY_SECRET')

    path = secrets_path or DEFAULT_SECRETS_PATH
    if os.path.exists(path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    if '=' in line:
                        k, v = line.split('=', 1)
                    elif ':' in line:
                        k, v = line.split(':', 1)
                    else:
                        continue
                    k = k.strip()
                    v = v.strip().strip('\"\'')
                    if k == 'API_KEY_ID' and not key_id:
                        key_id = v
                    elif k == 'RDW_API_KEY_SECRET' and not key_secret:
                        key_secret = v
        except Exception:
            pass

    return {
        'api_key_id': key_id,
        'api_key_secret': key_secret
    }

def load_zenodo_credentials(secrets_path: Optional[str] = None) -> Dict[str, Optional[str]]:
    """
    Safely retrieves Zenodo API Token from secrets file or environment variables.
    Never logs or echoes secret values.
    """
    token: Optional[str] = os.environ.get('ZENODO_API_TOKEN')

    path = secrets_path or DEFAULT_SECRETS_PATH
    if os.path.exists(path) and not token:
        try:
            with open(path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    if '=' in line:
                        k, v = line.split('=', 1)
                    elif ':' in line:
                        k, v = line.split(':', 1)
                    else:
                        continue
                    k = k.strip()
                    v = v.strip().strip('\"\'')
                    if k == 'ZENODO_API_TOKEN' and not token:
                        token = v
        except Exception:
            pass

    return {
        'zenodo_token': token
    }

def is_zenodo_configured(secrets_path: Optional[str] = None) -> bool:
    """Checks if Zenodo API Token is present and non-empty."""
    creds = load_zenodo_credentials(secrets_path)
    return bool(creds.get('zenodo_token'))

def get_zenodo_headers(secrets_path: Optional[str] = None) -> Dict[str, str]:
    """
    Constructs HTTP headers for Zenodo REST API.
    Uses Bearer token authentication per Zenodo API documentation.
    """
    headers: Dict[str, str] = {
        'User-Agent': 'SAS-Clinical-Research-Platform/1.0 (Zenodo Client)'
    }
    creds = load_zenodo_credentials(secrets_path)
    token = creds.get('zenodo_token')
    if token:
        headers['Authorization'] = f'Bearer {token}'
    return headers

def is_socrata_configured(secrets_path: Optional[str] = None) -> bool:
    """Checks if Socrata credentials are present and non-empty."""
    creds = load_socrata_credentials(secrets_path)
    return bool(creds.get('api_key_id') and creds.get('api_key_secret'))

def get_socrata_headers(secrets_path: Optional[str] = None) -> Dict[str, str]:
    """
    Constructs HTTP headers for Socrata SODA API.
    Uses HTTP Basic Authentication (API_KEY_ID:RDW_API_KEY_SECRET) per dev.socrata.com.
    """
    headers: Dict[str, str] = {
        'User-Agent': 'SAS-Clinical-Research-Platform/1.0',
        'Accept': 'text/csv'
    }
    creds = load_socrata_credentials(secrets_path)
    key_id = creds.get('api_key_id')
    key_secret = creds.get('api_key_secret')

    if key_id and key_secret:
        auth_bytes = f"{key_id}:{key_secret}".encode('utf-8')
        b64_auth = base64.b64encode(auth_bytes).decode('ascii')
        headers['Authorization'] = f'Basic {b64_auth}'

    return headers

def fetch_socrata_dataset(
    resource_url: str = DEFAULT_RDW_RESOURCE_URL,
    limit: int = 5000,
    offset: int = 0,
    where: Optional[str] = None,
    select: Optional[str] = None,
    order: Optional[str] = None,
    secrets_path: Optional[str] = None,
    timeout: int = 25
) -> Tuple[pd.DataFrame, bytes]:
    """
    Fetches tabular records from a Socrata SODA endpoint.
    Supports both SODA 3 Views Query API (/api/v3/views/{id}/query.csv)
    and classic SODA 2.x endpoints (/resource/{id}.csv).
    Returns (DataFrame, raw_csv_bytes).
    """
    is_soda3 = '/api/v3/views/' in resource_url

    if is_soda3:
        # SODA 3 Views Query API: uses SoQL SQL syntax in 'query' parameter
        soql_select = select or '*'
        soql_parts = [f"SELECT {soql_select}"]
        if where:
            soql_parts.append(f"WHERE {where}")
        if order:
            soql_parts.append(f"ORDER BY {order}")
        if limit:
            soql_parts.append(f"LIMIT {limit}")
        if offset:
            soql_parts.append(f"OFFSET {offset}")
        
        full_soql = " ".join(soql_parts)
        query_string = urllib.parse.urlencode({'query': full_soql})
        base_endpoint = resource_url.split('?')[0]
        full_url = f"{base_endpoint}?{query_string}"
    else:
        # SODA 2.x Resource API fallback
        if not resource_url.endswith('.csv') and not resource_url.endswith('.json'):
            resource_url = resource_url.rstrip('/') + '.csv'

        params = {'$limit': str(limit), '$offset': str(offset)}
        if where:
            params['$where'] = where
        if select:
            params['$select'] = select
        if order:
            params['$order'] = order

        query_string = urllib.parse.urlencode(params)
        full_url = f"{resource_url}?{query_string}" if params else resource_url

    headers = get_socrata_headers(secrets_path)
    req = urllib.request.Request(full_url, headers=headers)

    with urllib.request.urlopen(req, timeout=timeout) as response:
        raw_data = response.read()

    df = pd.read_csv(io.BytesIO(raw_data), low_memory=False)
    return df, raw_data

