import os
import pytest
import pypdf

REPORTS_DIR = os.path.join(os.path.dirname(__file__), '..', 'python', 'dashboard', 'static', 'reports')

class TestPDFStructure:

    def test_recent_pdf_reports_exist(self):
        pdf_files = [f for f in os.listdir(REPORTS_DIR) if f.lower().endswith('.pdf')]
        assert len(pdf_files) > 0, "At least one generated PDF report must exist in static/reports"

    def test_pdf_validity_and_page_structure(self):
        pdf_files = [f for f in os.listdir(REPORTS_DIR) if f.lower().endswith('.pdf')]
        pdf_files.sort(key=lambda f: os.path.getmtime(os.path.join(REPORTS_DIR, f)), reverse=True)
        target_pdf = os.path.join(REPORTS_DIR, pdf_files[0])
        
        reader = pypdf.PdfReader(target_pdf)
        # Spec: Report must have at least 2 pages (plots + tables)
        assert len(reader.pages) >= 2, f"Report {target_pdf} must contain at least 2 pages"

        # Check for presence of embedded images/vector figures or Figure 1 on Page 1
        page1 = reader.pages[0]
        page1_text = page1.extract_text()
        has_graphic = (len(page1.images) >= 1) or ('/XObject' in str(page1.get('/Resources', {}))) or ('Figure 1' in page1_text) or ('Scatterplot' in page1_text)
        assert has_graphic, "Page 1 must contain the graphical scatterplot visualization (Figure 1)"

    def test_pdf_summary_table_text(self):
        pdf_files = [f for f in os.listdir(REPORTS_DIR) if f.lower().endswith('.pdf')]
        pdf_files.sort(key=lambda f: os.path.getmtime(os.path.join(REPORTS_DIR, f)), reverse=True)
        target_pdf = os.path.join(REPORTS_DIR, pdf_files[0])
        
        reader = pypdf.PdfReader(target_pdf)
        all_text = " ".join([p.extract_text() for p in reader.pages])
        
        # Verify standard summary table markers produced by PROC PRINT
        assert "Week" in all_text or "Doses" in all_text, \
            f"Report {target_pdf} must contain data summary table with Week and Doses columns"

    def test_pdf_linked_tables_and_figures(self):
        pdf_files = [f for f in os.listdir(REPORTS_DIR) if f.lower().endswith('.pdf')]
        pdf_files.sort(key=lambda f: os.path.getmtime(os.path.join(REPORTS_DIR, f)), reverse=True)
        target_pdf = os.path.join(REPORTS_DIR, pdf_files[0])
        
        reader = pypdf.PdfReader(target_pdf)
        all_text = " ".join([p.extract_text() for p in reader.pages])

        # Verify linked Table IDs and Summary Table exist in text
        assert "Summary Table" in all_text, f"Report {target_pdf} must contain Executive Summary Table"
        assert "Table 1" in all_text, f"Report {target_pdf} must contain Table 1 linked to Figure 1"
        assert "Table 2" in all_text, f"Report {target_pdf} must contain Table 2 linked to Figure 2"
