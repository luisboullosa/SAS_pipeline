/******************************************************************************
* Macro: DALY_MACRO.SAS
* Purpose: Clinical & Epidemiological DALY Aggregation & Rate Standardization
* Reference: Dutch Public Health Foresight Study (VTV / PHFS)
*            Hilderink et al., Eur J Public Health 2025 (ckaf161.580)
******************************************************************************/

%macro calc_daly(
    data_in=,
    data_out=,
    pop_denominator=17800000
);
    data &data_out;
        set &data_in;
        
        /* Calculate YLL, YLD, and DALY rates per 10,000 population */
        daly_rate_10k = round((daly / &pop_denominator) * 10000, 0.01);
        yll_rate_10k  = round((yll / &pop_denominator) * 10000, 0.01);
        yld_rate_10k  = round((yld / &pop_denominator) * 10000, 0.01);
        
        /* Proportions */
        if daly > 0 then do;
            yll_share_pct = round((yll / daly) * 100, 0.1);
            yld_share_pct = round((yld / daly) * 100, 0.1);
        end;
        else do;
            yll_share_pct = 0;
            yld_share_pct = 0;
        end;
        
        format daly yll yld comma14.0
               daly_rate_10k yll_rate_10k yld_rate_10k 8.2
               yll_share_pct yld_share_pct 5.1;
    run;
%mend calc_daly;

%macro rank_burdens(
    data_in=,
    data_out=,
    by_var=Year Gender Age_Stratum,
    order_var=DALY,
    top_n=10
);
    proc sort data=&data_in out=work._sorted_burdens;
        by &by_var descending &order_var;
    run;

    data &data_out;
        set work._sorted_burdens;
        by &by_var;
        
        retain disease_rank;
        if first.%scan(&by_var, -1, %str( )) then disease_rank = 0;
        disease_rank + 1;
        
        if disease_rank <= &top_n;
    run;
%mend rank_burdens;
