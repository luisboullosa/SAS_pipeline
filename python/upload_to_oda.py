"""
Script to upload clinical and epidemiological showcase data and SAS code 
to SAS OnDemand for Academics (ODA).
"""

import os
import sys
import saspy

RELATIVE_FILES_TO_UPLOAD = [
    # SAS Templates
    "sas_templates/graph_templates.sas",
    "sas_templates/macros.sas",
    "sas_templates/styles.sas",
    
    # Dutch PHFS Burden of Disease Project - SAS Code
    "projects/dutch_phfs_burden_of_disease/sas/daly_macro.sas",
    "projects/dutch_phfs_burden_of_disease/sas/phfs_nature_report.sas",
    "projects/dutch_phfs_burden_of_disease/sas/vtv_trendscenario_data.sas",
    "projects/dutch_phfs_burden_of_disease/sas/vtv_trendscenario_report.sas",
    
    # Dutch PHFS Burden of Disease Project - Data & Documentation
    "projects/dutch_phfs_burden_of_disease/data/dutch_dalys_estimates.csv",
    "projects/dutch_phfs_burden_of_disease/data/dutch_dalys_summary.csv",
    "projects/dutch_phfs_burden_of_disease/README.md",
    
    # Clinical Data (SDTM, ADaM, Raw, COVID)
    "data/raw/dm.csv",
    "data/raw/ta.csv",
    "data/sdtm/DM_py.csv",
    "data/adam/ADSL_EPOCH_py.csv",
    "data/covid/data.csv",
    
    # Longevity General Linear Model Project
    "projects/longevity_linear_model/life_expectancy_glm.sas",
    "projects/longevity_linear_model/data/global_longevity_gdp.csv",
    "projects/longevity_linear_model/run_model.py",
]

def resolve_remote_base(sas):
    """
    Resolves the remote home directory dynamically from environment or active SAS session.
    """
    env_base = os.environ.get("SAS_REMOTE_BASE")
    if env_base:
        return env_base.rstrip("/")
    try:
        user_res = sas.submit("data _null_; put 'SYSUSERID=' \"&sysuserid\"; run;")
        log = user_res.get("LOG", "")
        for line in log.splitlines():
            if "SYSUSERID=" in line:
                user = line.split("SYSUSERID=")[1].strip().strip('"')
                if user:
                    return f"/home/{user}/SAS"
    except Exception:
        pass
    return "/home/sasuser/SAS"

def ensure_remote_dir(sas, remote_dir_path):
    """
    Ensures that a remote directory path exists on the SAS server by creating
    any missing parent and child folders sequentially using SAS dcreate().
    """
    parts = [p for p in remote_dir_path.strip("/").split("/") if p]
    current = ""
    for part in parts:
        if not current:
            current = "/" + part
            continue
        parent = current
        current = f"{current}/{part}"
        
        check_code = f"""
        data _null_;
            rc = filename('_chkdir', '{current}');
            did = dopen('_chkdir');
            if did > 0 then do;
                put 'DIR_EXISTS=1';
                rc = dclose(did);
            end;
            else do;
                newdir = dcreate('{part}', '{parent}');
                put 'CREATED_DIR=' newdir;
            end;
            rc = filename('_chkdir');
        run;
        """
        sas.submit(check_code)

def upload_all():
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    cfg_path = os.path.join(os.path.dirname(__file__), "sascfg_personal.py")
    
    print("=========================================================")
    print("Connecting to SAS OnDemand for Academics (ODA)...")
    print("=========================================================")
    sas = saspy.SASsession(cfgfile=cfg_path, cfgname="oda")
    print("Connected successfully.\n")
    
    remote_base = resolve_remote_base(sas)
    print(f"Resolved remote base directory: {remote_base}")

    files_to_upload = [
        (rel, f"{remote_base}/{rel}") for rel in RELATIVE_FILES_TO_UPLOAD
    ]
    
    # 1. Collect all directories that need to be created
    remote_dirs = set()
    for local_rel, remote_file in files_to_upload:
        remote_dirs.add(os.path.dirname(remote_file).replace("\\", "/"))
    
    sorted_dirs = sorted(list(remote_dirs), key=lambda d: len(d.split("/")))
    
    print("Creating remote directory structure on SAS server...")
    for rdir in sorted_dirs:
        ensure_remote_dir(sas, rdir)
        print(f"  [OK] Directory verified: {rdir}")
        
    print("\n=========================================================")
    print(f"Uploading {len(files_to_upload)} files to {remote_base}...")
    print("=========================================================\n")
    
    success_count = 0
    failed_count = 0
    
    for local_rel, remote_file in files_to_upload:
        local_path = os.path.join(root_dir, local_rel)
        if not os.path.exists(local_path):
            print(f"  [MISSING] Local file not found: {local_path}")
            failed_count += 1
            continue
            
        file_size_kb = os.path.getsize(local_path) / 1024
        print(f"Uploading: {local_rel} ({file_size_kb:.1f} KB)")
        print(f"       --> {remote_file}")
        
        res = sas.upload(local_path, remote_file, overwrite=True)
        if res.get("Success", False):
            print("       --> [SUCCESS]")
            success_count += 1
        else:
            print(f"       --> [FAILED] {res.get('LOG', '')}")
            failed_count += 1
            
    print("\n=========================================================")
    print(f"Upload Complete: {success_count} succeeded, {failed_count} failed.")
    print("=========================================================")
    
    sas.disconnect()
    print("Disconnected from SAS session.")

if __name__ == "__main__":
    upload_all()
