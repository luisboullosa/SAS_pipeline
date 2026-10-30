"""
CBS Open Data (cbsodata) Client for Dutch Public Health Foresight Study (VTV/PHFS)
Extracts morbidity, mortality, and life expectancy tables directly from Statistics Netherlands (CBS).
Caches extractions in high-speed columnar Parquet format.
"""

import os
import re
import json
import time
from typing import Optional, Dict, List, Any
import pandas as pd
import cbsodata

# Core CBS OData Tables for VTV / PHFS
CBS_TABLE_VTV_MORBIDITY = "84067NED"       # Ziekenhuisopnamen; diagnose-indeling VTV
CBS_TABLE_MORTALITY_CAUSES = "7052_95"      # Overledenen; belangrijke doodsoorzaken
CBS_TABLE_HEALTHY_LIFE_EXP = "71950ned"    # Gezonde levensverwachting

# Standard Clinical VTV Taxonomy Mapping (matches CBS decoded titles)
VTV_DISEASE_MAP = {
    "Totaal alle diagnosen": "All Causes (Total)",
    "2 Totaal nieuwvormingen": "All Cancers & Neoplasms",
    "2.1.4 Dikkedarmkanker": "Colorectal Cancer",
    "2.1.7 Longkanker": "Trachea, Bronchus & Lung Cancer",
    "2.1.10 Borstkanker": "Breast Cancer",
    "2.1.13 Prostaatkanker": "Prostate Cancer",
    "4.2 Diabetes mellitus (suikerziekte)": "Diabetes Mellitus",
    "5 Totaal psychische en gedragsstoorn.": "Mental & Behavioral Disorders",
    "5.7.1 Depressieve stoornissen": "Major Depressive Disorders",
    "9 Totaal zkt. van hart- en vaatstelsel": "Cardiovascular & Circulatory Diseases",
    "9.3 Coronaire hartziekten": "Coronary Artery Disease (IHD)",
    "9.6 Hartfalen": "Heart Failure",
    "10 Totaal zkt. van de ademhalingsorganen": "Respiratory & Pulmonary Diseases",
    "13 Totaal zkt. spier, beenderen, bindw.": "Musculoskeletal & Joint Diseases",
    "19 Totaal ongevalsletsel en vergiftiging": "Accidental Injuries & Poisonings",
    "21 Totaal COVID-19": "COVID-19 Inpatient Morbidity"
}

# Standardized RIVM Disability Weights (DW) parameterization (Global Burden of Disease / RIVM 2024 update)
RIVM_DISABILITY_WEIGHTS = {
    "All Causes (Total)": 0.120,
    "Infectious & Parasitic Diseases": 0.085,
    "All Cancers & Neoplasms": 0.288,
    "Colorectal Cancer": 0.290,
    "Trachea, Bronchus & Lung Cancer": 0.450,
    "Breast Cancer": 0.210,
    "Prostate Cancer": 0.180,
    "Diabetes Mellitus": 0.075,
    "Mental & Behavioral Disorders": 0.220,
    "Major Depressive Disorders": 0.295,
    "Nervous System Disorders": 0.310,
    "Cardiovascular & Circulatory Diseases": 0.195,
    "Coronary Artery Disease (IHD)": 0.210,
    "Heart Failure": 0.280,
    "Respiratory & Pulmonary Diseases": 0.185,
    "Digestive System Diseases": 0.090,
    "Musculoskeletal & Joint Diseases": 0.145,
    "Accidental Injuries & Poisonings": 0.150,
    "COVID-19 Inpatient Morbidity": 0.210
}

GENDER_MAP = {
    "T001038": "Both Sexes",
    "Totaal mannen en vrouwen": "Both Sexes",
    "3000": "Male",
    "Mannen": "Male",
    "4000": "Female",
    "Vrouwen": "Female"
}

def clean_period_label(p_key: str) -> str:
    """Standardizes CBS period keys (e.g. '2022JJ00' -> '2022')."""
    if not p_key:
        return ""
    match = re.match(r"^(\d{4})", str(p_key))
    return match.group(1) if match else str(p_key)

class CBSVTVClient:
    """Client for querying and harmonizing Statistics Netherlands (CBS) VTV health data."""

    def __init__(self, cache_dir: Optional[str] = None):
        self.cache_dir = cache_dir or os.path.abspath(
            os.path.join(os.path.dirname(__file__), "data")
        )
        os.makedirs(self.cache_dir, exist_ok=True)

    def fetch_vtv_hospital_morbidity(
        self,
        years: Optional[List[str]] = None,
        force_refresh: bool = False
    ) -> pd.DataFrame:
        """
        Fetches VTV diagnosis hospital admissions from CBS 84067NED.
        Filters by total admission type (SoortOpname eq 'T001389') for specified years.
        """
        parquet_path = os.path.join(self.cache_dir, "cbs_vtv_hospital_morbidity.parquet")
        if not force_refresh and os.path.exists(parquet_path):
            return pd.read_parquet(parquet_path)

        target_years = years or ["2020", "2021", "2022", "2023"]
        period_filters = [f"Perioden eq '{yr}JJ00'" for yr in target_years]
        period_filter_clause = f"({' or '.join(period_filters)})" if len(period_filters) > 1 else period_filters[0]

        filter_query = f"SoortOpname eq 'T001389' and {period_filter_clause}"
        print(f"Fetching CBS {CBS_TABLE_VTV_MORBIDITY} with filter: {filter_query}")

        data = cbsodata.get_data(CBS_TABLE_VTV_MORBIDITY, filters=filter_query)
        df = pd.DataFrame(data)

        # Standardize columns and dimensions
        df["Year"] = df["Perioden"].apply(clean_period_label)
        df["Gender"] = df["Geslacht"].map(GENDER_MAP).fillna(df["Geslacht"])
        df["Disease_Code"] = df["DiagnoseIndelingVTV"]
        df["Disease_Name"] = df["DiagnoseIndelingVTV"].map(VTV_DISEASE_MAP).fillna("Other Specific Diagnosis")

        # Save to Parquet
        df.to_parquet(parquet_path, engine="pyarrow", compression="snappy")
        return df

    def fetch_cause_specific_mortality(
        self,
        years: Optional[List[str]] = None,
        force_refresh: bool = False
    ) -> pd.DataFrame:
        """
        Fetches cause-specific mortality from CBS 7052_95.
        """
        parquet_path = os.path.join(self.cache_dir, "cbs_cause_specific_mortality.parquet")
        if not force_refresh and os.path.exists(parquet_path):
            return pd.read_parquet(parquet_path)

        target_years = years or ["2020", "2021", "2022", "2023"]
        period_filters = [f"Perioden eq '{yr}JJ00'" for yr in target_years]
        period_filter_clause = f"({' or '.join(period_filters)})" if len(period_filters) > 1 else period_filters[0]

        print(f"Fetching CBS {CBS_TABLE_MORTALITY_CAUSES} with filter: {period_filter_clause}")
        data = cbsodata.get_data(CBS_TABLE_MORTALITY_CAUSES, filters=period_filter_clause)
        df = pd.DataFrame(data)

        df["Year"] = df["Perioden"].apply(clean_period_label)
        df["Gender"] = df["Geslacht"].map(GENDER_MAP).fillna(df["Geslacht"])

        df.to_parquet(parquet_path, engine="pyarrow", compression="snappy")
        return df

    def fetch_healthy_life_expectancy(self, force_refresh: bool = False) -> pd.DataFrame:
        """
        Fetches healthy life expectancy from CBS 71950ned.
        """
        parquet_path = os.path.join(self.cache_dir, "cbs_healthy_life_expectancy.parquet")
        if not force_refresh and os.path.exists(parquet_path):
            return pd.read_parquet(parquet_path)

        print(f"Fetching CBS {CBS_TABLE_HEALTHY_LIFE_EXP}...")
        data = cbsodata.get_data(CBS_TABLE_HEALTHY_LIFE_EXP)
        df = pd.DataFrame(data)

        df["Year"] = df["Perioden"].apply(clean_period_label)
        df["Gender"] = df["Geslacht"].map(GENDER_MAP).fillna(df["Geslacht"])

        df.to_parquet(parquet_path, engine="pyarrow", compression="snappy")
        return df
