import os
import pandas as pd
import saspy

def run_sas_pipeline():
    print("Starting SAS Clinical Pipeline via saspy...")
    
    # 1. Connect to SAS ODA using the 'oda' configuration
    try:
        # Note: sascfg_personal.py should be in this directory and _authinfo in your home directory
        sas = saspy.SASsession(cfgname='oda')
        print("SAS Session started successfully.")
    except Exception as e:
        print("Could not start SAS session. Please ensure sascfg_personal.py is correct and _authinfo is set up.")
        print(e)
        return

    # 2. Upload source data to SAS WORK library
    dm_path = r"D:\Development\SAS\data\raw\dm.csv"
    ta_path = r"D:\Development\SAS\data\raw\ta.csv"
    
    print("Loading data into SAS WORK library...")
    dm_df = pd.read_csv(dm_path)
    ta_df = pd.read_csv(ta_path)
    
    sas.df2sd(dm_df, table="DM", libref="WORK")
    sas.df2sd(ta_df, table="TA", libref="WORK")
    
    # 3. Submit SAS code for Macros & Pipeline Data Processing
    sas_code = """
    /* Macro 1: Date Standardization */
    %macro std_date(indsn, outdsn, invar, outvar);
        data &outdsn;
            set &indsn;
            /* Dummy data is already YYYY-MM-DD string, so we just copy it. 
               Real implementation would parse and format. */
            &outvar = &invar; 
        run;
    %mend;

    /* Macro 2: Calculate Interval (e.g. End Day) */
    %macro calc_interval(indsn, outdsn, startdt, enddt, outvar);
        data &outdsn;
            set &indsn;
            _start = input(&startdt, yymmdd10.);
            _end = input(&enddt, yymmdd10.);
            if _end >= _start then &outvar = _end - _start + 1;
            else if _end ne . and _start ne . then &outvar = _end - _start;
            drop _start _end;
        run;
    %mend;

    /* Macro 3: Derive EPOCH */
    %macro derive_epoch(indsn_dm, indsn_ta, outdsn);
        proc sql noprint;
            create table &outdsn as
            select a.*, b.EPOCH
            from &indsn_dm a
            left join &indsn_ta b
            on a.STUDYID = b.STUDYID and a.ARMCD = b.ARMCD;
        quit;
    %mend;

    /* Execute the Pipeline */
    %std_date(WORK.DM, WORK.DM_STD, BRTHDTC, BRTHDTC_STD);
    %calc_interval(WORK.DM_STD, WORK.DM_INT, RFSTDTC, RFENDTC, RFENDY);
    %derive_epoch(WORK.DM_INT, WORK.TA, WORK.ADSL_EPOCH);
    """
    
    print("Executing SAS Pipeline macros and logic...")
    res = sas.submit(sas_code)
    
    # Print the SAS log for debugging/confirmation
    if res.get('LOG'):
        print("\n--- SAS LOG SNIPPET ---")
        lines = res['LOG'].split('\n')
        # Print a snippet of the log (first 15 and last 15 lines)
        if len(lines) > 30:
            print('\\n'.join(lines[:15]))
            print("...[LOG TRUNCATED]...")
            print('\\n'.join(lines[-15:]))
        else:
            print(res['LOG'])
        print("-----------------------\n")
        
    # 4. Pull datasets back and export to CSVs
    sdtm_out = r"D:\Development\SAS\data\sdtm\DM_sas.csv"
    adam_out = r"D:\Development\SAS\data\adam\ADSL_EPOCH_sas.csv"
    
    print("Pulling processed datasets back from SAS and exporting...")
    try:
        dm_final_df = sas.sd2df(table="DM_INT", libref="WORK")
        adsl_final_df = sas.sd2df(table="ADSL_EPOCH", libref="WORK")
        
        dm_final_df.to_csv(sdtm_out, index=False)
        adsl_final_df.to_csv(adam_out, index=False)
        
        print(f"Exported SDTM DM (via SAS) to {sdtm_out}")
        print(f"Exported ADaM ADSL with EPOCH (via SAS) to {adam_out}")
    except Exception as e:
        print("Error pulling data from SAS:")
        print(e)
        
    sas.disconnect()

if __name__ == "__main__":
    run_sas_pipeline()
