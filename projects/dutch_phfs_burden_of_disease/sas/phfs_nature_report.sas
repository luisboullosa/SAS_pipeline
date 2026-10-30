/******************************************************************************
* Program: PHFS_NATURE_REPORT.SAS
* Purpose: Nature Journal-Style Clinical Report for Dutch Burden of Disease
* Reference: Dutch Public Health Foresight Study (VTV / PHFS)
*            Hilderink et al., Eur J Public Health 2025 (ckaf161.580)
* Data: CBS Open Data 84067NED & 7052_95 via cbsodata
******************************************************************************/

/* Load macros */
%include "daly_macro.sas";

/* Options for Nature journal high-resolution PDF rendering */
options nodate nonumber orientation=portrait linesize=120 pagesize=80;

/* Define Nature Publication ODS Style */
proc template;
    define style styles.nature_phfs;
        parent = styles.listing;
        style GraphFonts from GraphFonts /
            'GraphTitleFont' = ("Arial, Helvetica", 11pt, bold)
            'GraphLabelFont' = ("Arial, Helvetica", 9pt, bold)
            'GraphValueFont' = ("Arial, Helvetica", 8pt)
            'GraphDataFont'  = ("Arial, Helvetica", 8pt);
        style Table from Table /
            frame = hsides
            rules = groups
            cellpadding = 4pt
            cellspacing = 0pt
            bordercollapse = collapse
            bordercolor = #262626
            borderwidth = 0.5pt;
        style Header from Header /
            backgroundcolor = #f7f7f7
            color = #000000
            fontfamily = "Arial, Helvetica"
            fontsize = 8.5pt
            fontweight = bold;
        style Data from Data /
            backgroundcolor = #ffffff
            color = #262626
            fontfamily = "Arial, Helvetica"
            fontsize = 8pt;
    end;
run;

/* Import Processed DALY Estimates */
proc import datafile="../data/dutch_dalys_estimates.csv"
    out=work.daly_estimates
    dbms=csv
    replace;
    guessingrows=2000;
run;

/* Standardize & Filter for Reporting */
%calc_daly(
    data_in=work.daly_estimates,
    data_out=work.daly_calculated,
    pop_denominator=17800000
);

/* Top 10 National Burden (Both Sexes, Total Age, Latest Year) */
data work.top10_national;
    set work.daly_calculated;
    where Year = "2023" and Gender = "Both Sexes" and Age_Stratum = "Total" and Disease_Name ne "All Causes (Total)";
run;

%rank_burdens(
    data_in=work.top10_national,
    data_out=work.top10_ranked,
    by_var=Year Gender Age_Stratum,
    order_var=DALY,
    top_n=10
);

/* ODS PDF Output Setup */
ods listing close;
ods pdf file="../data/Dutch_PHFS_DALY_Report_Nature.pdf"
    style=styles.nature_phfs
    dpi=300
    notoc;

ods text="^S={font_face='Arial' font_size=14pt font_weight=bold color=#000000}Dutch Public Health Foresight Study: National Burden of Disease (DALYs)^n";
ods text="^S={font_face='Arial' font_size=9pt color=#52525b}Methodological Framework: RIVM & CBS Open Data • Reference: Hilderink et al., Eur J Public Health 2025 (doi: 10.1093/eurpub/ckaf161.580)^n^n";

/* SECTION 1: Executive Summary Table */
ods text="^S={font_face='Arial' font_size=10pt font_weight=bold color=#000000}Executive Summary: National Disease Burden Overview (2023)^n";

proc report data=work.top10_ranked split='*';
    column disease_rank Disease_Name DALY daly_rate_10k YLL yll_share_pct YLD yld_share_pct;
    define disease_rank / "Rank" style(column)={width=6% justification=c};
    define Disease_Name / "Disease / Health Condition" style(column)={width=34%};
    define DALY / "DALYs*(Total Burden)" format=comma12. style(column)={width=15% justification=r};
    define daly_rate_10k / "Rate per*10,000" format=8.2 style(column)={width=11% justification=r};
    define YLL / "YLL*(Mortality)" format=comma12. style(column)={width=13% justification=r};
    define yll_share_pct / "YLL %" format=5.1 style(column)={width=8% justification=r};
    define YLD / "YLD*(Disability)" format=comma12. style(column)={width=13% justification=r};
    define yld_share_pct / "YLD %" format=5.1 style(column)={width=8% justification=r};
run;

ods startpage=now;

/* SECTION 2: Figure 1 & Linked Table 1 */
ods text="^S={font_face='Arial' font_size=10pt font_weight=bold color=#000000}Figure 1: Top 10 Causes of Disease Burden (DALYs) in the Netherlands (2023)^n";

proc sgplot data=work.top10_ranked;
    hbar Disease_Name / response=DALY categoryorder=respasc
         fillattrs=(color=#2563eb) datalabel;
    xaxis label="Disability-Adjusted Life Years (DALYs)" grid;
    yaxis label="" discreteorder=data;
run;

ods text="^S={font_face='Arial' font_size=8pt italic color=#52525b}Figure 1 Note: Total DALYs aggregated across inpatient hospital admissions and mortality registers. Linked to Table 1.^n^n";

ods text="^S={font_face='Arial' font_size=10pt font_weight=bold color=#000000}Table 1: Top 10 Disease Burden Estimates and Share of Premature Mortality (YLL)^n";

proc report data=work.top10_ranked;
    column disease_rank Disease_Name DALY YLL yll_share_pct;
    define disease_rank / "Rank" style(column)={justification=c};
    define Disease_Name / "Disease Category";
    define DALY / "Total DALYs" format=comma12. style(column)={justification=r};
    define YLL / "Years of Life Lost (YLL)" format=comma12. style(column)={justification=r};
    define yll_share_pct / "Mortality Share (%)" format=5.1 style(column)={justification=r};
run;

ods startpage=now;

/* SECTION 3: Figure 2 & Linked Table 2 - Age Breakdown */
data work.age_trajectories;
    set work.daly_calculated;
    where Year = "2023" and Gender = "Both Sexes" and Age_Stratum in ("<15", "15-24", "25-44", "45-64", "65-74", "75+")
          and Disease_Name in ("All Cancers & Neoplasms", "Cardiovascular & Circulatory Diseases", "Major Depressive Disorders", "Respiratory & Pulmonary Diseases");
run;

ods text="^S={font_face='Arial' font_size=10pt font_weight=bold color=#000000}Figure 2: Age-Specific Burden Trajectories for Selected Disease Classes (2023)^n";

proc sgplot data=work.age_trajectories;
    series x=Age_Stratum y=DALY / group=Disease_Name lineattrs=(thickness=2pt) markers;
    xaxis label="Age Cohort Stratum" grid;
    yaxis label="Disability-Adjusted Life Years (DALYs)" grid;
    keylegend / position=bottom across=2;
run;

ods text="^S={font_face='Arial' font_size=8pt italic color=#52525b}Figure 2 Note: Illustrates the steep age gradient for circulatory disease and neoplasms compared to early-life mental health burdens. Linked to Table 2.^n^n";

ods text="^S={font_face='Arial' font_size=10pt font_weight=bold color=#000000}Table 2: DALY Distribution by Age Strata for Key Public Health Priority Conditions^n";

proc report data=work.age_trajectories;
    column Disease_Name Age_Stratum DALY daly_rate_10k;
    define Disease_Name / "Health Condition" order;
    define Age_Stratum / "Age Stratum";
    define DALY / "Total DALYs" format=comma12. style(column)={justification=r};
    define daly_rate_10k / "Rate per 10,000" format=8.2 style(column)={justification=r};
run;

ods pdf close;
ods listing;
