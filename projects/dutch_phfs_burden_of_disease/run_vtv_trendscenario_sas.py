"""
Recreates all VTV-2024 Trendscenario findings in native SAS.
Connects via saspy, runs vtv_trendscenario_report.sas, downloads and verifies the generated publication PDF.
Source: https://www.volksgezondheidtoekomstverkenning.nl/vtv-2024/trendscenario
"""

import os
import sys
import pypdf

PROJECT_DIR = os.path.abspath(os.path.dirname(__file__))
ROOT_DIR = os.path.abspath(os.path.join(PROJECT_DIR, "..", ".."))
sys.path.insert(0, os.path.join(ROOT_DIR, "python"))

import saspy

def main():
    print("================================================================================")
    print("Executing RIVM VTV-2024 Trendscenario Recreation in Native SAS")
    print("Reference: https://www.volksgezondheidtoekomstverkenning.nl/vtv-2024/trendscenario")
    print("================================================================================")

    sas_dir = os.path.join(PROJECT_DIR, "sas")
    data_sas_file = os.path.join(sas_dir, "vtv_trendscenario_data.sas")
    report_sas_file = os.path.join(sas_dir, "vtv_trendscenario_report.sas")
    
    with open(data_sas_file, 'r', encoding='utf-8') as f:
        data_code = f.read()

    with open(report_sas_file, 'r', encoding='utf-8') as f:
        report_code = f.read()

    # Inline data code into report code to guarantee standalone execution on SAS ODA
    full_sas_code = report_code.replace('%include "vtv_trendscenario_data.sas";', data_code)

    print("Connecting to SAS session (ODA)...")
    sas = saspy.SASsession(cfgname='oda')
    print("Active SAS Session established.")

    # Submit the SAS code
    print("Submitting SAS VTV-2024 Trendscenario code...")
    res = sas.submit(full_sas_code)

    workpath = sas.symget('workpath').strip()
    remote_pdf = f"{workpath}/VTV_2024_Trendscenario_Nature_Report.pdf"
    local_pdf = os.path.join(PROJECT_DIR, "data", "VTV_2024_Trendscenario_Nature_Report.pdf")
    
    print(f"Downloading report from remote SAS server ({remote_pdf})...")
    sas.download(local_pdf, remote_pdf)

    if os.path.exists(local_pdf) and os.path.getsize(local_pdf) > 0:
        pdf_kb = os.path.getsize(local_pdf) / 1024
        print(f"\nSUCCESS: Generated Publication PDF Report: {local_pdf} ({pdf_kb:.1f} KB)")
        
        # Verify PDF structure using pypdf
        reader = pypdf.PdfReader(local_pdf)
        print(f"Total Pages Rendered in Nature PDF: {len(reader.pages)}")
        
        # Extract sample text from page 1 & page 2
        page1_text = reader.pages[0].extract_text()
        print("\n--- Page 1 Executive Summary Text Excerpt ---")
        for line in page1_text.splitlines()[:12]:
            if line.strip():
                print(" ", line.strip())
    else:
        print(f"\nError: PDF download did not produce a valid file.")

    # Terminate cleanly
    sas.endsas()
    print("\nSAS Session terminated cleanly.")

if __name__ == "__main__":
    main()
