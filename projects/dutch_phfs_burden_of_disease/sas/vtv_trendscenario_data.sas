/******************************************************************************
* Program: VTV_TRENDSCENARIO_DATA.SAS
* Purpose: Canonical Dataset Compilation for RIVM VTV-2024 Trendscenario
* Source:  Rijksinstituut voor Volksgezondheid en Milieu (RIVM) & CBS
* URL:     https://www.volksgezondheidtoekomstverkenning.nl/vtv-2024/trendscenario
* Horizon: 1990 - 2022 (Historical Observed) to 2050 (Trend Projection)
******************************************************************************/

/* 1. Life Expectancy Trajectory (1990 - 2050) */
data work.vtv_life_expectancy;
    input Year Male Female Total HLE_GoodHealth HLE_NoDisability;
    datalines;
1990 73.8 80.1 77.0 61.3 66.2
1995 74.6 80.4 77.5 61.4 65.5
2000 75.5 80.6 78.1 61.4 68.3
2005 77.2 81.6 79.5 62.3 68.5
2010 78.8 82.7 80.8 63.9 69.8
2015 79.7 83.1 81.5 64.4 70.8
2018 80.2 83.3 81.8 63.8 72.0
2019 80.5 83.6 82.0 64.4 72.1
2020 79.7 83.1 81.4 66.5 72.3
2021 79.7 83.0 81.3 65.6 73.1
2022 80.1 83.1 81.6 63.2 71.2
2023 80.4 83.5 81.9 65.2 72.3
2025 80.8 83.9 82.4 65.5 72.7
2030 81.7 84.9 83.3 66.2 73.4
2035 82.5 85.7 84.1 66.7 73.9
2040 83.2 86.5 84.9 67.2 74.3
2045 84.0 87.3 85.6 67.8 74.7
2050 84.8 88.2 86.5 68.8 75.0
;
run;

/* 2. Survival Probability by Age Milestones (1990 - 2050) */
data work.vtv_survival_prob;
    input Year Prob_65 Prob_75 Prob_85 Prob_100;
    datalines;
1990 0.852 0.663 0.337 0.009
1995 0.860 0.678 0.350 0.008
2000 0.869 0.697 0.368 0.009
2005 0.885 0.734 0.416 0.012
2010 0.898 0.764 0.467 0.017
2015 0.906 0.779 0.493 0.016
2019 0.913 0.793 0.518 0.019
2020 0.911 0.784 0.488 0.013
2021 0.908 0.778 0.490 0.014
2022 0.911 0.785 0.503 0.013
2025 0.918 0.805 0.531 0.016
2030 0.926 0.824 0.565 0.021
2035 0.933 0.841 0.597 0.025
2040 0.939 0.854 0.622 0.028
2045 0.946 0.871 0.651 0.035
2050 0.952 0.885 0.689 0.042
;
run;

/* 3. Chronic Condition Burden by Age Group (2022 - 2050) */
data work.vtv_chronic_by_age;
    input Year Age_Group $ Pop_With_Chronic;
    datalines;
2022 0-64 7225908
2022 65-74 1718330
2022 75+ 1536716
2025 0-64 7302397
2025 65-74 1788978
2025 75+ 1762506
2030 0-64 7204025
2030 65-74 1955188
2030 75+ 2062450
2035 0-64 7147685
2035 65-74 2013586
2035 75+ 2270592
2040 0-64 7208822
2040 65-74 1924514
2040 75+ 2484275
2045 0-64 7376109
2045 65-74 1739320
2045 75+ 2706432
2050 0-64 7529493
2050 65-74 1677414
2050 75+ 2790039
;
run;

/* 4. Top Chronic Conditions Comparison (2022 vs 2050 Prevalence) */
data work.vtv_top_conditions;
    length Condition $40;
    input Condition $ & Prev_2022 Prev_2050;
    Diff_Abs = Prev_2050 - Prev_2022;
    Pct_Change = round(((Prev_2050 - Prev_2022) / Prev_2022) * 100, 0.1);
    datalines;
Artrose (Osteoarthritis) 1671900 2977800
Nek- en rugklachten 1851700 2193700
Gezichtsstoornissen (Vision) 1003900 1409400
Angststoornissen (Anxiety) 1275200 1376500
Diabetes Mellitus 1166600 1246600
Nierfalen (Kidney Failure) 736600 1153300
Gehoorstoornissen (Hearing) 800100 1133500
Stemmingsstoornissen (Depression) 841000 906300
Schildklierziekten 677700 821400
Hartritmestoornissen 483300 768300
Coronaire hartziekten 795800 697800
Contacteczeem 879000 542800
;
run;

/* 5. Disease Burden Shift (DALYs: 2022 vs 2050) */
data work.vtv_daly_shift;
    length Disease $40;
    input Disease $ & DALY_2022 DALY_2050;
    DALY_Change_Pct = round(((DALY_2050 - DALY_2022) / DALY_2022) * 100, 0.1);
    datalines;
Dementie (Dementia) 140700 346300
Stemmingsstoornissen (Depression) 270800 290800
Ongevallen (Falls & Injuries) 127100 192300
Nek- en rugklachten 147400 183200
COPD 192000 178300
Angststoornissen 159700 171500
Nierfalen 106700 171500
Artrose 64000 121800
Alcohol gerelateerd 111000 117600
Diabetes 110400 108000
Longkanker 155900 106200
Beroerte (Stroke) 135000 95800
;
run;

/* 6. Cause of Death Shift (2022 vs 2050 Deaths) */
data work.vtv_cause_death_shift;
    length Cause_Group $45;
    input Cause_Group $ & Deaths_2022 Deaths_2050 Rank_2022 Rank_2050;
    Delta_Deaths = Deaths_2050 - Deaths_2022;
    datalines;
Nieuwvormingen (Cancers) 47500 47100 1 1
Psychische stoornissen (Dementie) 13000 36000 3 2
Ziekten ademhalingswegen (Resp) 12900 24800 4 3
Uitwendige oorzaken (Ongevallen) 10500 21500 5 4
Zenuwstelsel en zintuigen 9100 20000 7 5
Hart- en vaatstelsel (Cardio) 39000 18900 2 6
Symptomen & onvolledig omschreven 10600 8600 6 7
Urogenitaal stelsel 3800 8500 8 8
Infectieuze en parasitaire zktn 3100 6200 9 9
;
run;

/* 7. Socioeconomic Inequality in Health (Education Gradient) */
data work.vtv_ses_inequality;
    length Education_Level $25 Indicator $35;
    input Education_Level $ Indicator $ Value_Years;
    datalines;
Laag Levensverwachting 78.4
Middelbaar Levensverwachting 81.1
Hoog Levensverwachting 83.3
Laag Gezonde_Levensverwachting 53.6
Middelbaar Gezonde_Levensverwachting 61.2
Hoog Gezonde_Levensverwachting 68.2
;
run;
