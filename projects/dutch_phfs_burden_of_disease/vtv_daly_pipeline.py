"""
Dutch Public Health Foresight Study (VTV/PHFS) DALY Estimation Pipeline
Computes Years of Life Lost (YLL), Years Lived with Disability (YLD), and DALYs
based on Statistics Netherlands (CBS) and RIVM burden of disease methodologies.
Reference: Hilderink et al., Eur J Public Health 2025 (doi: 10.1093/eurpub/ckaf161.580).
"""

import os
import sys
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple

from cbs_client import (
    CBSVTVClient,
    VTV_DISEASE_MAP,
    RIVM_DISABILITY_WEIGHTS,
    clean_period_label
)

# Standard WHO / GBD reference life expectancy by age bracket (aspirational benchmark)
STANDARD_LIFE_EXPECTANCY_TABLE = {
    "<15": 73.2,
    "15-24": 63.8,
    "25-44": 49.5,
    "45-64": 31.2,
    "65-74": 16.8,
    "75+": 8.4,
    "Total": 32.5
}

# Mapping of CBS Age codes/labels (Leeftijd) in 84067NED to standard epidemiological age strata
def map_cbs_age_stratum(leeftijd_val: str) -> str:
    s = str(leeftijd_val).strip().lower()
    if s in ["10000"] or "totaal" in s:
        return "Total"
    if s in ["10010", "51300", "70200", "70300", "0 jaar", "1 tot 5 jaar", "5 tot 10 jaar", "10 tot 15 jaar"] or "<15" in s:
        return "<15"
    if s in ["70400", "70500", "15 tot 20 jaar", "20 tot 25 jaar"] or "15-24" in s:
        return "15-24"
    if s in ["70600", "70700", "70800", "70900", "25 tot 30 jaar", "30 tot 35 jaar", "35 tot 40 jaar", "40 tot 45 jaar"] or "25-44" in s:
        return "25-44"
    if s in ["71000", "71100", "71200", "71300", "45 tot 50 jaar", "50 tot 55 jaar", "55 tot 60 jaar", "60 tot 65 jaar"] or "45-64" in s:
        return "45-64"
    if s in ["71400", "71500", "65 tot 70 jaar", "70 tot 75 jaar"] or "65-74" in s:
        return "65-74"
    if s in ["71600", "71700", "71800", "71900", "72000", "21700", "22000", "75 tot 80 jaar", "80 tot 85 jaar", "85 tot 90 jaar", "90 tot 95 jaar", "95 jaar of ouder", "65 jaar of ouder", "80 jaar of ouder"] or "75+" in s:
        return "75+"
    return "Other"

class VTVDALYPipeline:
    """Orchestrates extraction, harmonization, and DALY computation for Dutch PHFS."""

    def __init__(self, data_dir: Optional[str] = None):
        self.data_dir = data_dir or os.path.abspath(
            os.path.join(os.path.dirname(__file__), "data")
        )
        self.client = CBSVTVClient(cache_dir=self.data_dir)

    def run_pipeline(
        self,
        years: Optional[List[str]] = None,
        force_refresh: bool = False
    ) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Executes end-to-end data pull and DALY calculations.
        Returns (detailed_df, summary_df).
        """
        analysis_years = years or ["2020", "2021", "2022", "2023"]

        print("\n--- Step 1: Ingesting CBS VTV Hospital Morbidity (84067NED) ---")
        df_morb = self.client.fetch_vtv_hospital_morbidity(years=analysis_years, force_refresh=force_refresh)

        # Match disease names via VTV_DISEASE_MAP
        df_morb["Disease_Name"] = df_morb["DiagnoseIndelingVTV"].map(VTV_DISEASE_MAP)
        df_morb_filtered = df_morb[df_morb["Disease_Name"].notna()].copy()
        df_morb_filtered["Disease_Code"] = df_morb_filtered["DiagnoseIndelingVTV"]
        df_morb_filtered["Age_Stratum"] = df_morb_filtered["Leeftijd"].apply(map_cbs_age_stratum)
        df_morb_filtered["Inpatient_Admissions"] = pd.to_numeric(df_morb_filtered["Opnamen_1"], errors="coerce").fillna(0)
        df_morb_filtered["Inpatient_Rate_Per10k"] = pd.to_numeric(df_morb_filtered["OpnamenPer10000Inwoners_2"], errors="coerce").fillna(0)
        df_morb_filtered["Disability_Weight"] = df_morb_filtered["Disease_Name"].map(RIVM_DISABILITY_WEIGHTS).fillna(0.150)

        # Aggregate morbidity by Year, Gender, Age_Stratum, Disease_Name
        agg_morb = df_morb_filtered.groupby(
            ["Year", "Gender", "Age_Stratum", "Disease_Code", "Disease_Name"],
            as_index=False
        ).agg({
            "Inpatient_Admissions": "sum",
            "Inpatient_Rate_Per10k": "mean",
            "Disability_Weight": "first"
        })

        agg_morb["Gender"] = agg_morb["Gender"].map({
            "Totaal mannen en vrouwen": "Both Sexes",
            "Mannen": "Male",
            "Vrouwen": "Female",
            "Both Sexes": "Both Sexes",
            "Male": "Male",
            "Female": "Female"
        }).fillna(agg_morb["Gender"])

        print("\n--- Step 2: Computing Years Lived with Disability (YLD) ---")
        # YLD = Prevalent Inpatient Burden * Disability Weight (average 1-year episode)
        agg_morb["YLD"] = agg_morb["Inpatient_Admissions"] * agg_morb["Disability_Weight"]

        print("\n--- Step 3: Deriving Years of Life Lost (YLL) & Total DALYs ---")
        # Standard mortality estimation proportional to disease fatality profile
        FATALITY_RATIOS = {
            "All Causes (Total)": 0.082,
            "Infectious & Parasitic Diseases": 0.045,
            "All Cancers & Neoplasms": 0.320,
            "Colorectal Cancer": 0.280,
            "Trachea, Bronchus & Lung Cancer": 0.650,
            "Breast Cancer": 0.160,
            "Prostate Cancer": 0.140,
            "Diabetes Mellitus": 0.055,
            "Mental & Behavioral Disorders": 0.025,
            "Major Depressive Disorders": 0.015,
            "Nervous System Disorders": 0.110,
            "Cardiovascular & Circulatory Diseases": 0.180,
            "Coronary Artery Disease (IHD)": 0.220,
            "Heart Failure": 0.260,
            "Respiratory & Pulmonary Diseases": 0.120,
            "Digestive System Diseases": 0.035,
            "Musculoskeletal & Joint Diseases": 0.005,
            "Accidental Injuries & Poisonings": 0.075,
            "COVID-19 Inpatient Morbidity": 0.140
        }

        agg_morb["Fatality_Ratio"] = agg_morb["Disease_Name"].map(FATALITY_RATIOS).fillna(0.050)
        agg_morb["Estimated_Deaths"] = agg_morb["Inpatient_Admissions"] * agg_morb["Fatality_Ratio"]
        agg_morb["Standard_LE"] = agg_morb["Age_Stratum"].map(STANDARD_LIFE_EXPECTANCY_TABLE).fillna(25.0)

        # YLL = Estimated Deaths * Residual Life Expectancy
        agg_morb["YLL"] = agg_morb["Estimated_Deaths"] * agg_morb["Standard_LE"]

        # DALY = YLL + YLD
        agg_morb["DALY"] = agg_morb["YLL"] + agg_morb["YLD"]

        # Component percentage breakdowns
        agg_morb["YLL_Pct"] = np.where(agg_morb["DALY"] > 0, (agg_morb["YLL"] / agg_morb["DALY"]) * 100.0, 0.0)
        agg_morb["YLD_Pct"] = np.where(agg_morb["DALY"] > 0, (agg_morb["YLD"] / agg_morb["DALY"]) * 100.0, 0.0)

        # Standard population denominators for rates (Netherlands approx 17.8M in 2022)
        DUTCH_POPULATION = 17800000
        agg_morb["DALY_Rate_Per10k"] = (agg_morb["DALY"] / (DUTCH_POPULATION / 10000.0)).round(2)

        # Rank diseases within Year and Gender
        agg_morb["Disease_Rank"] = agg_morb.groupby(["Year", "Gender", "Age_Stratum"])["DALY"].rank(
            ascending=False, method="min"
        )

        print("\n--- Step 4: Exporting Standardized Analysis Products ---")
        parquet_out = os.path.join(self.data_dir, "dutch_dalys_estimates.parquet")
        csv_out = os.path.join(self.data_dir, "dutch_dalys_estimates.csv")
        summary_out = os.path.join(self.data_dir, "dutch_dalys_summary.csv")

        agg_morb.to_parquet(parquet_out, engine="pyarrow", compression="snappy")
        agg_morb.to_csv(csv_out, index=False)

        # Summary table for reporting: Total age, Both sexes, Latest year
        latest_year = max(analysis_years)
        summary_df = agg_morb[
            (agg_morb["Year"] == latest_year) &
            (agg_morb["Gender"] == "Both Sexes") &
            (agg_morb["Age_Stratum"] == "Total") &
            (agg_morb["Disease_Name"] != "All Causes (Total)")
        ].sort_values("DALY", ascending=False).reset_index(drop=True)

        summary_df["Rank"] = range(1, len(summary_df) + 1)
        summary_df.to_csv(summary_out, index=False)

        print(f"Successfully generated {len(agg_morb)} stratified estimates.")
        print(f"Top 5 Disease Burdens in {latest_year} (Netherlands):")
        for idx, row in summary_df.head(5).iterrows():
            print(f"  #{row['Rank']}: {row['Disease_Name']} — {row['DALY']:,.0f} DALYs (YLL: {row['YLL_Pct']:.1f}%, YLD: {row['YLD_Pct']:.1f}%)")

        return agg_morb, summary_df

if __name__ == "__main__":
    pipeline = VTVDALYPipeline()
    pipeline.run_pipeline()
