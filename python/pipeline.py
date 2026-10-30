import os
import pandas as pd
import saspy

def run_pipeline():
    print("Starting Python Clinical Pipeline...")
    
    # 1. Read source data
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    dm_path = os.path.join(base_dir, "data", "raw", "dm.csv")
    ta_path = os.path.join(base_dir, "data", "raw", "ta.csv")
    
    dm_df = pd.read_csv(dm_path)
    ta_df = pd.read_csv(ta_path)
    
    # 2. Date Standardization
    # Convert string to datetime, then back to ISO format string
    dm_df['BRTHDTC_STD'] = pd.to_datetime(dm_df['BRTHDTC']).dt.strftime('%Y-%m-%d')
    
    # 3. Calculation of interval (SDTM style: end - start + 1 if end >= start)
    start_dates = pd.to_datetime(dm_df['RFSTDTC'])
    end_dates = pd.to_datetime(dm_df['RFENDTC'])
    diff_days = (end_dates - start_dates).dt.days
    dm_df['RFENDY'] = diff_days.apply(lambda x: x + 1 if pd.notnull(x) and x >= 0 else x)
    
    # 4. Derivation of EPOCH from T domains / DM dataset
    # Merge DM and TA
    dm_with_epoch = pd.merge(dm_df, ta_df, on=["STUDYID", "ARMCD", "ARM"], how="left")
    
    # 5. Exporting
    sdtm_out = os.path.join(base_dir, "data", "sdtm", "DM_py.csv")
    adam_out = os.path.join(base_dir, "data", "adam", "ADSL_EPOCH_py.csv")
    
    dm_df.to_csv(sdtm_out, index=False)
    dm_with_epoch.to_csv(adam_out, index=False)
    print(f"Exported SDTM DM to {sdtm_out}")
    print(f"Exported ADaM ADSL with EPOCH to {adam_out}")
    
    # Optional: Connect to SAS using saspy if a SAS instance is available
    try:
        print("Attempting to connect to SAS via saspy...")
        sas = saspy.SASsession()
        print("SAS Session started successfully.")
        
        # We can push pandas dataframe to SAS
        sas_dm = sas.df2sd(dm_df, table="DM", libref="WORK")
        print("Dataframe pushed to SAS WORK.DM")
        
        # Example of running a SAS macro from Python
        # sas.submit(
        #     '''
        #     %macro calc_interval(start, end, out);
        #         &out = &end - &start + 1;
        #     %mend;
        #     '''
        # )
        
        sas.disconnect()
    except Exception as e:
        print("SAS session could not be started. (This is expected if SAS is not installed locally)")
        print(e)

if __name__ == "__main__":
    run_pipeline()
