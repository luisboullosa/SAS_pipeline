import pytest
from datetime import datetime

def standardize_date(raw_date_str):
    """CDISC ISO 8601 clinical date standardization specification."""
    if not raw_date_str:
        return None
    raw = str(raw_date_str).strip()
    formats = ['%d-%b-%Y', '%d%b%Y', '%Y-%m-%d', '%m/%d/%Y', '%d/%m/%Y', '%Y.%m.%d']
    for fmt in formats:
        try:
            dt = datetime.strptime(raw, fmt)
            return dt.strftime('%Y-%m-%d')
        except ValueError:
            pass
    return None

def calculate_study_interval(start_date_str, end_date_str):
    """CDISC study day interval specification: End - Start + 1 (no Day 0)."""
    if not start_date_str or not end_date_str:
        return None
    d_start = datetime.strptime(start_date_str, '%Y-%m-%d')
    d_end = datetime.strptime(end_date_str, '%Y-%m-%d')
    delta = (d_end - d_start).days
    if delta >= 0:
        return delta + 1
    return None

def derive_epoch(arm, visit_num):
    """Clinical Trial EPOCH derivation specification based on ARM and Visit."""
    if visit_num < 1:
        return 'SCREENING'
    elif 1 <= visit_num <= 10:
        return 'TREATMENT'
    else:
        return 'FOLLOW-UP'


class TestClinicalSpecifications:

    @pytest.mark.parametrize("raw_input,expected", [
        ("01-JAN-2021", "2021-01-01"),
        ("15-AUG-2022", "2022-08-15"),
        ("2023-05-20", "2023-05-20"),
        ("12/31/2020", "2020-12-31"),
        ("2021.07.04", "2021-07-04"),
    ])
    def test_iso8601_date_standardization(self, raw_input, expected):
        assert standardize_date(raw_input) == expected

    def test_invalid_date_handling(self):
        assert standardize_date("INVALID_DATE") is None
        assert standardize_date("") is None
        assert standardize_date(None) is None

    def test_study_interval_boundary_conditions(self):
        # Same day: Day 1
        assert calculate_study_interval("2021-01-01", "2021-01-01") == 1
        # Consecutive days: Day 2
        assert calculate_study_interval("2021-01-01", "2021-01-02") == 2
        # Full month
        assert calculate_study_interval("2021-01-01", "2021-01-31") == 31
        # End before Start: invalid interval
        assert calculate_study_interval("2021-02-01", "2021-01-01") is None

    def test_epoch_derivation(self):
        assert derive_epoch("ARM_A", 0) == 'SCREENING'
        assert derive_epoch("ARM_A", 1) == 'TREATMENT'
        assert derive_epoch("ARM_A", 10) == 'TREATMENT'
        assert derive_epoch("ARM_A", 11) == 'FOLLOW-UP'
