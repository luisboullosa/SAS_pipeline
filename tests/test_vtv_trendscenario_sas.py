"""
Tests for Native SAS Recreation of RIVM VTV-2024 Trendscenario
Validates SAS datasets, report generator, and rendered 5-page publication PDF.
Reference: https://www.volksgezondheidtoekomstverkenning.nl/vtv-2024/trendscenario
"""

import os
import pytest
import pypdf

PROJECT_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "projects", "dutch_phfs_burden_of_disease")
)
SAS_DIR = os.path.join(PROJECT_DIR, "sas")
DATA_DIR = os.path.join(PROJECT_DIR, "data")
PDF_REPORT = os.path.join(DATA_DIR, "VTV_2024_Trendscenario_Nature_Report.pdf")

class TestVTVTrendscenarioSAS:

    def test_sas_source_files_exist(self):
        """Verifies that SAS data compilation and reporting programs exist."""
        data_sas = os.path.join(SAS_DIR, "vtv_trendscenario_data.sas")
        report_sas = os.path.join(SAS_DIR, "vtv_trendscenario_report.sas")
        runner_py = os.path.join(PROJECT_DIR, "run_vtv_trendscenario_sas.py")
        
        assert os.path.exists(data_sas)
        assert os.path.exists(report_sas)
        assert os.path.exists(runner_py)

    def test_sas_data_contains_key_pillars(self):
        """Checks that vtv_trendscenario_data.sas contains the empirical and projected numbers."""
        data_sas = os.path.join(SAS_DIR, "vtv_trendscenario_data.sas")
        with open(data_sas, "r", encoding="utf-8") as f:
            content = f.read()

        # Pillar 1: Life Expectancy
        assert "86.5" in content
        assert "77.0" in content
        # Pillar 2: Survival
        assert "Prob_100" in content
        assert "0.042" in content
        # Pillar 3: Chronic Diseases
        assert "7225908" in content
        # Pillar 4: Top Conditions (Artrose surge)
        assert "Artrose" in content
        assert "2977800" in content
        # Pillar 5: DALYs (Dementia surge)
        assert "346300" in content
        # Pillar 6: Cause of Death Shift
        assert "47100" in content
        assert "18900" in content
        # Pillar 7: SES Inequalities
        assert "14.6" in content or "53.6" in content

    def test_vtv_trendscenario_pdf_exists_and_valid(self):
        """Validates that the 300-DPI Nature Journal PDF was compiled with 5 pages."""
        assert os.path.exists(PDF_REPORT), f"Missing PDF report: {PDF_REPORT}"
        assert os.path.getsize(PDF_REPORT) > 20000  # At least 20 KB
        
        reader = pypdf.PdfReader(PDF_REPORT)
        assert len(reader.pages) == 5

    def test_vtv_trendscenario_pdf_content_verification(self):
        """Inspects text content of rendered PDF to verify all key findings are documented."""
        reader = pypdf.PdfReader(PDF_REPORT)
        full_text = "\n".join(page.extract_text() for page in reader.pages)

        # Executive synthesis & LE
        assert "Trendscenario" in full_text
        assert "86.5" in full_text
        assert "Levensverwachting" in full_text
        
        # Survival probabilities
        assert "Pillar" in full_text
        assert "68.9%" in full_text or "68.9" in full_text
        
        # Chronic condition & DALYs
        assert "Artrose" in full_text or "Osteoarthritis" in full_text
        assert "Dementie" in full_text or "Dementia" in full_text
        
        # Inequalities
        assert "Gezonde" in full_text or "Inequality" in full_text
