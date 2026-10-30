"""
Orchestration Script: Global Life Expectancy General Linear Model in Native SAS
Executes life_expectancy_glm.sas via saspy, extracts statistical tables,
and downloads the publication PDF report.
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
    print("Executing Global Life Expectancy GLM / Multiple Linear Regression in Native SAS")
    print("Model: Life_Expectancy = ln(GDP) + Health_Expenditure_Pct + Region (ANCOVA)")
    print("================================================================================")

    sas_script_path = os.path.join(PROJECT_DIR, "life_expectancy_glm.sas")
    with open(sas_script_path, "r", encoding="utf-8") as f:
        sas_code = f.read()

    print("\n[Step 1] Connecting to SAS Session (ODA / Local)...")
    cfg_path = os.path.join(ROOT_DIR, "python", "sascfg_personal.py")
    sas = saspy.SASsession(cfgfile=cfg_path, cfgname="oda")
    print("SAS Session established successfully.")

    # Initialize workpath in SAS session
    local_csv = os.path.join(PROJECT_DIR, "data", "global_longevity_gdp.csv")
    sas.submit("%let workpath = %sysfunc(pathname(work));")
    workpath = sas.symget("workpath").strip()
    remote_csv = f"{workpath}/global_longevity_gdp.csv"
    
    print(f"\n[Step 2] Uploading dataset to SAS server ({local_csv} -> {remote_csv})...")
    sas.upload(local_csv, remote_csv)

    # Direct SAS code to use the uploaded remote CSV in WORK
    init_stmt = f"%let data_file = {remote_csv};\n"
    adapted_code = init_stmt + sas_code

    print("\n[Step 3] Submitting SAS GLM / Multiple Regression code...")
    res = sas.submit(adapted_code)

    # Check for SAS errors in log
    log_text = res.get("LOG", "")
    has_error = "ERROR:" in log_text
    if has_error:
        print("\n--- SAS LOG EXCERPT (ERRORS FOUND) ---")
        for line in log_text.splitlines():
            if "ERROR:" in line or "WARNING:" in line:
                print(" ", line)
    else:
        print("SAS code executed cleanly without errors.")

    # Step 4: Pull back statistical results into Pandas
    print("\n[Step 4] Retrieving Model Parameter Estimates & Goodness-of-Fit...")
    try:
        df_params = sas.sd2df("params_display", "work")
        df_fit = sas.sd2df("model_fit", "work")
        df_anova = sas.sd2df("model_anova", "work")

        print("\n--- MODEL GOODNESS-OF-FIT ---")
        print(df_fit.to_string(index=False))

        print("\n--- OVERALL ANOVA TABLE ---")
        print(df_anova.to_string(index=False))

        print("\n--- PARAMETER ESTIMATES & P-VALUES ---")
        if df_params is not None:
            cols_to_show = [c for c in ["Parameter", "Estimate", "StdErr", "tValue", "Probt", "LowerCL", "UpperCL", "Significance"] if c in df_params.columns]
            print(df_params[cols_to_show].to_string(index=False))
    except Exception as e:
        print(f"Notice extracting SAS datasets: {e}")

    # Step 5: Download generated publication PDF report
    print("\n[Step 5] Downloading Nature-styled PDF Report...")
    remote_pdf = f"{workpath}/Life_Expectancy_Linear_Model_Report.pdf"
    local_pdf = os.path.join(PROJECT_DIR, "data", "Life_Expectancy_Linear_Model_Report.pdf")

    sas.download(local_pdf, remote_pdf)

    if os.path.exists(local_pdf) and os.path.getsize(local_pdf) > 0:
        pdf_size_kb = os.path.getsize(local_pdf) / 1024
        print(f"SUCCESS: Report saved to {local_pdf} ({pdf_size_kb:.1f} KB)")

        # Verify PDF structure
        reader = pypdf.PdfReader(local_pdf)
        print(f"Report Rendered: {len(reader.pages)} page(s)")
    else:
        print(f"Warning: PDF file was not created or empty at {local_pdf}")

    sas.disconnect()
    print("\nSAS Session terminated cleanly.")

if __name__ == "__main__":
    main()
