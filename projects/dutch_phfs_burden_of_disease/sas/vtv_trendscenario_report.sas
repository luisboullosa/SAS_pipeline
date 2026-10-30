/******************************************************************************
* Program: VTV_TRENDSCENARIO_REPORT.SAS
* Purpose: Nature Journal-Style Comprehensive Report of VTV-2024 Trendscenario
* Source:  Rijksinstituut voor Volksgezondheid en Milieu (RIVM) & CBS
* URL:     https://www.volksgezondheidtoekomstverkenning.nl/vtv-2024/trendscenario
* Standards: Nature/Ecology style, 300 DPI vector graphics, linked tables & figures
******************************************************************************/

/* Load canonical datasets */
%include "vtv_trendscenario_data.sas";

/* Options for Nature journal high-resolution PDF rendering */
options nodate nonumber orientation=portrait linesize=132 pagesize=90;

/* Define Nature Publication ODS Style */
proc template;
    define style styles.nature_vtv;
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
            backgroundcolor = #f4f4f5
            color = #000000
            fontfamily = "Arial, Helvetica"
            fontsize = 8.5pt
            fontweight = bold;
        style Data from Data /
            backgroundcolor = #ffffff
            color = #18181b
            fontfamily = "Arial, Helvetica"
            fontsize = 8pt;
    end;
run;

/* Master Synthesis Table Data */
data work.vtv_master_summary;
    length Domain $35 Indicator $40 Metric_2022 $20 Metric_2050 $20 Trend_Description $45;
    input Domain $ & Indicator $ & Metric_2022 $ & Metric_2050 $ & Trend_Description $;
    datalines;
Levensverwachting Levensverwachting Totaal 81.6 jaar 86.5 jaar +4.9 jaar toename (gestaag herstel na COVID)
Levensverwachting Levensverwachting Mannen 80.1 jaar 84.8 jaar +4.7 jaar toename
Levensverwachting Levensverwachting Vrouwen 83.1 jaar 88.2 jaar +5.1 jaar toename (vrouwenverschil blijft 3-3.5j)
Gezonde Levensjaren Goede Ervaren Gezondheid 63.2 jaar 68.8 jaar +5.6 jaar toename (meer gezonde jaren)
Gezonde Levensjaren Zonder Beperkingen 71.2 jaar 75.0 jaar +3.8 jaar toename (+1.2 jaar met beperking)
Overleving Kans op leeftijd 85 bereiken 50.3% 68.9% Toename van 1 op 2 naar ruim 2 op 3
Overleving Kans op leeftijd 100 bereiken 1.3% 4.2% Ruim verdrievoudiging (1 op 24 wordt 100+)
Chronische Ziekten Personen met >=1 aandoening 10.5 miljoen 12.0 miljoen +1.5 miljoen (+1.3M onder 75-plussers)
Chronische Ziekten Multimorbiditeit (>=3 aand.) 3.3 miljoen 4.3 miljoen Sterke toename meervoudige aandoeningen
Top Aandoening Meest voorkomend in 2050 Artrose (1.67M) Artrose (2.98M) Sprong naar #1 chronische aandoening
Ziektelast (DALY) Belangrijkste oorzaak Stemming (271k) Dementie (346k) Dementie stijgt met +146% naar absolute #1
Doodsoorzaken Verschuiving #2 Doodsoorzaak Hart- en vaatziekten Dementie / Psych Hartvaat daalt naar #6; Dementie naar #2
Gezondheidsverschil Gezonde levensjaren Laag vs Hoog 53.6 vs 68.2 jaar 53.6 vs 68.2 jaar Hardnekkige kloof van 14.6 jaar
;
run;

/* ODS PDF Setup */
ods listing close;
ods escapechar='^';
title;
footnote;
%let workpath = %sysfunc(pathname(work));
ods pdf file="&workpath/VTV_2024_Trendscenario_Nature_Report.pdf"
    style=styles.nature_vtv
    dpi=300
    notoc;

/* ========================================================================== */
/* PAGE 1: EXECUTIVE SYNTHESIS                                                */
/* ========================================================================== */
ods text="^S={font_face='Arial' font_size=15pt font_weight=bold color=#000000}RIVM Public Health Foresight Study: Trendscenario 2022–2050^n";
ods text="^S={font_face='Arial' font_size=9pt color=#52525b}National Institute for Public Health and the Environment (RIVM) & Statistics Netherlands (CBS) • SAS Replication Analysis^n";
ods text="^S={font_face='Arial' font_size=8.5pt italic color=#71717a}Source: https://www.volksgezondheidtoekomstverkenning.nl/vtv-2024/trendscenario • Projections through 2050^n^n";

ods text="^S={font_face='Arial' font_size=10.5pt font_weight=bold color=#000000}Executive Summary: Master Findings & Strategic Projections (2022 vs. 2050)^n";

proc report data=work.vtv_master_summary split='*';
    column Domain Indicator Metric_2022 Metric_2050 Trend_Description;
    define Domain / "Domain" order style(column)={width=16% font_weight=bold};
    define Indicator / "Indicator / Horizon" style(column)={width=22%};
    define Metric_2022 / "Baseline (2022)" style(column)={width=13% justification=r};
    define Metric_2050 / "Projected (2050)" style(column)={width=14% justification=r};
    define Trend_Description / "Trend Dynamic & Epidemiological Context" style(column)={width=35%};
run;

ods text="^S={font_face='Arial' font_size=8pt italic color=#71717a}^nNote: Trendscenario assumes continuation of existing policies and historical trends without major systemic policy interventions.^n";

ods startpage=now;

/* ========================================================================== */
/* PAGE 2: LIFE EXPECTANCY & SURVIVAL TRAJECTORIES (1990 - 2050)              */
/* ========================================================================== */
ods text="^S={font_face='Arial' font_size=11pt font_weight=bold color=#000000}Pillar 1: Life Expectancy Trajectory & Longevity Frontier (1990–2050)^n";
ods text="^S={font_face='Arial' font_size=8.5pt color=#52525b}Figure 1: Observed and projected life expectancy at birth in the Netherlands for Total, Men, and Women.^n";

proc sgplot data=work.vtv_life_expectancy;
    series x=Year y=Total / lineattrs=(color=#2563eb thickness=2.5pt) legendlabel="Total Population" datalabel;
    series x=Year y=Male / lineattrs=(color=#059669 thickness=1.5pt pattern=shortdash) legendlabel="Men";
    series x=Year y=Female / lineattrs=(color=#dc2626 thickness=1.5pt pattern=shortdash) legendlabel="Women";
    refline 2022 / axis=x lineattrs=(color=#a1a1aa pattern=dot) label="Baseline (2022)";
    xaxis label="Calendar Year" grid values=(1990 to 2050 by 10);
    yaxis label="Life Expectancy at Birth (Years)" grid min=70 max=90;
    keylegend / position=bottom across=3;
run;

ods text="^S={font_face='Arial' font_size=8pt italic color=#71717a}Figure 1 Note: Total life expectancy rises from 81.6 years in 2022 to 86.5 years in 2050. The female advantage remains stable at 3.4 years. Linked to Table 1.^n^n";

ods text="^S={font_face='Arial' font_size=10pt font_weight=bold color=#000000}Table 1: Life Expectancy and Healthy Longevity Milestones (Selected Years)^n";

proc report data=work.vtv_life_expectancy(where=(Year in (1990, 2000, 2010, 2019, 2020, 2022, 2030, 2040, 2050)));
    column Year Total Male Female HLE_GoodHealth HLE_NoDisability;
    define Year / "Year" style(column)={justification=c font_weight=bold};
    define Total / "Total LE" format=5.1 style(column)={justification=r};
    define Male / "Men LE" format=5.1 style(column)={justification=r};
    define Female / "Women LE" format=5.1 style(column)={justification=r};
    define HLE_GoodHealth / "Healthy LE (Good Health)" format=5.1 style(column)={justification=r};
    define HLE_NoDisability / "Disability-Free LE" format=5.1 style(column)={justification=r};
run;

ods text="^S={font_face='Arial' font_size=11pt font_weight=bold color=#000000}^nPillar 2: Cumulative Survival Probability to Milestone Ages (1990–2050)^n";

proc sgplot data=work.vtv_survival_prob;
    series x=Year y=Prob_65 / lineattrs=(color=#2563eb thickness=2pt) legendlabel="Reach Age 65";
    series x=Year y=Prob_75 / lineattrs=(color=#059669 thickness=2pt) legendlabel="Reach Age 75";
    series x=Year y=Prob_85 / lineattrs=(color=#d97706 thickness=2pt) legendlabel="Reach Age 85";
    series x=Year y=Prob_100 / lineattrs=(color=#dc2626 thickness=2pt pattern=shortdash) legendlabel="Reach Age 100";
    refline 2022 / axis=x lineattrs=(color=#a1a1aa pattern=dot) label="Baseline (2022)";
    xaxis label="Calendar Year" grid values=(1990 to 2050 by 10);
    yaxis label="Survival Probability (0 to 1)" grid min=0 max=1 format=percent7.1;
    keylegend / position=bottom across=4;
run;

ods text="^S={font_face='Arial' font_size=8pt italic color=#71717a}Figure 2 Note: The chance of reaching age 85 increases from 50.3% to 68.9%. The chance of becoming a centenarian (100+) expands from 1.3% to 4.2% (over 3x increase).^n";

ods startpage=now;

/* ========================================================================== */
/* PAGE 3: CHRONIC CONDITIONS & MULTIMORBIDITY EXPANSION                      */
/* ========================================================================== */
ods text="^S={font_face='Arial' font_size=11pt font_weight=bold color=#000000}Pillar 3: Chronic Disease Population & Age Stratification (2022–2050)^n";
ods text="^S={font_face='Arial' font_size=8.5pt color=#52525b}Figure 3: Growth in individuals living with chronic illness by age cohort.^n";

proc sgplot data=work.vtv_chronic_by_age;
    vbar Year / response=Pop_With_Chronic group=Age_Group groupdisplay=stack;
    xaxis label="Calendar Horizon Year" discreteorder=data;
    yaxis label="Individuals with Chronic Disease" grid format=comma12.;
    keylegend / position=bottom across=3 title="Age Stratum:";
run;

ods text="^S={font_face='Arial' font_size=8pt italic color=#71717a}Figure 3 Note: Population with chronic illness increases by 1.5 million to 12.0 million in 2050, with 87% (+1.3 million) concentrated among individuals aged 75 and older. Linked to Table 2.^n^n";

ods text="^S={font_face='Arial' font_size=11pt font_weight=bold color=#000000}Pillar 4: Top Chronic Conditions in 2050 (Baseline vs. Projected Prevalence)^n";

proc sgplot data=work.vtv_top_conditions;
    hbar Condition / response=Prev_2050 fillattrs=(color=#2563eb) legendlabel="2050 Projected" datalabel;
    hbar Condition / response=Prev_2022 fillattrs=(color=#94a3b8) legendlabel="2022 Baseline" barwidth=0.4;
    xaxis label="Prevalent Population" grid format=comma12.;
    yaxis label="" discreteorder=data;
    keylegend / position=bottom across=2;
run;

ods text="^S={font_face='Arial' font_size=8pt italic color=#71717a}Figure 4 Note: Artrose (osteoarthritis) surges to become the #1 chronic condition in the Netherlands with nearly 3.0 million patients in 2050 (+78.1% growth). Linked to Table 3.^n^n";

ods text="^S={font_face='Arial' font_size=10pt font_weight=bold color=#000000}Table 3: Top Chronic Conditions Ranked by 2050 Prevalence and Growth Rate^n";

proc report data=work.vtv_top_conditions;
    column Condition Prev_2022 Prev_2050 Diff_Abs Pct_Change;
    define Condition / "Chronic Condition" style(column)={width=38% font_weight=bold};
    define Prev_2022 / "2022 Patients" format=comma12. style(column)={width=16% justification=r};
    define Prev_2050 / "2050 Patients" format=comma12. style(column)={width=16% justification=r};
    define Diff_Abs / "Absolute Growth" format=comma12. style(column)={width=16% justification=r};
    define Pct_Change / "Growth (%)" format=5.1 style(column)={width=14% justification=r};
run;

ods startpage=now;

/* ========================================================================== */
/* PAGE 4: EPIDEMIOLOGICAL PARADIGM SHIFT (DALYs & CAUSE OF DEATH)            */
/* ========================================================================== */
ods text="^S={font_face='Arial' font_size=11pt font_weight=bold color=#000000}Pillar 5: National Disease Burden Shift (DALYs: 2022 vs. 2050)^n";
ods text="^S={font_face='Arial' font_size=8.5pt color=#52525b}Figure 5: Total Disability-Adjusted Life Years (DALY = YLL + YLD) by primary condition.^n";

proc sgplot data=work.vtv_daly_shift;
    hbar Disease / response=DALY_2050 fillattrs=(color=#7c3aed) legendlabel="2050 DALYs" datalabel;
    hbar Disease / response=DALY_2022 fillattrs=(color=#cbd5e1) legendlabel="2022 DALYs" barwidth=0.4;
    xaxis label="Disability-Adjusted Life Years (DALYs)" grid format=comma12.;
    yaxis label="" discreteorder=data;
    keylegend / position=bottom across=2;
run;

ods text="^S={font_face='Arial' font_size=8pt italic color=#71717a}Figure 5 Note: Dementia burden increases by +146.1% to 346,300 DALYs, surpassing mood disorders to become the single largest source of disease burden in the Netherlands. Linked to Table 4.^n^n";

ods text="^S={font_face='Arial' font_size=11pt font_weight=bold color=#000000}Pillar 6: Historic Transition in Causes of Death (Mortality Shift)^n";

proc sgplot data=work.vtv_cause_death_shift;
    hbar Cause_Group / response=Deaths_2050 fillattrs=(color=#dc2626) legendlabel="2050 Deaths" datalabel;
    hbar Cause_Group / response=Deaths_2022 fillattrs=(color=#94a3b8) legendlabel="2022 Deaths" barwidth=0.4;
    xaxis label="Annual Underlying Deaths" grid format=comma12.;
    yaxis label="" discreteorder=data;
    keylegend / position=bottom across=2;
run;

ods text="^S={font_face='Arial' font_size=8pt italic color=#71717a}Figure 6 Note: Cardiovascular disease mortality drops from #2 (39,000) to #6 (18,900) due to prevention and interventions, while dementia/psychiatric mortality rises to #2 (36,000). Linked to Table 5.^n^n";

ods text="^S={font_face='Arial' font_size=10pt font_weight=bold color=#000000}Table 5: Primary Cause of Death Transitions and Rank Trajectories (2022 vs. 2050)^n";

proc report data=work.vtv_cause_death_shift;
    column Rank_2022 Rank_2050 Cause_Group Deaths_2022 Deaths_2050 Delta_Deaths;
    define Rank_2022 / "Rank '22" style(column)={width=10% justification=c};
    define Rank_2050 / "Rank '50" style(column)={width=10% justification=c font_weight=bold};
    define Cause_Group / "Cause of Death Classification" style(column)={width=36%};
    define Deaths_2022 / "2022 Deaths" format=comma10. style(column)={width=14% justification=r};
    define Deaths_2050 / "2050 Deaths" format=comma10. style(column)={width=14% justification=r};
    define Delta_Deaths / "Net Change" format=comma10. style(column)={width=16% justification=r};
run;

ods startpage=now;

/* ========================================================================== */
/* PAGE 5: SOCIOECONOMIC HEALTH INEQUALITIES & POLICY HORIZON                 */
/* ========================================================================== */
ods text="^S={font_face='Arial' font_size=11pt font_weight=bold color=#000000}Pillar 7: Socioeconomic Inequality in Life Expectancy & Health Gaps^n";
ods text="^S={font_face='Arial' font_size=8.5pt color=#52525b}Figure 7: Total Life Expectancy vs. Healthy Life Expectancy by educational attainment.^n";

proc sgplot data=work.vtv_ses_inequality;
    vbar Education_Level / response=Value_Years group=Indicator groupdisplay=cluster
         fillattrs=(color=#0284c7) datalabel;
    xaxis label="Educational Attainment Level" discreteorder=data;
    yaxis label="Years of Expected Life" grid min=40 max=90;
    keylegend / position=bottom across=2;
run;

ods text="^S={font_face='Arial' font_size=8pt italic color=#71717a}Figure 7 Note: While the total life expectancy gap between low and high education is 4.9 years, the gap in Healthy Life Expectancy reaches 14.6 years (53.6 vs. 68.2 years). Linked to Table 6.^n^n";

ods text="^S={font_face='Arial' font_size=10pt font_weight=bold color=#000000}Table 6: Educational Disparities in Longevity and Perceived Health Horizon^n";

proc report data=work.vtv_ses_inequality;
    column Education_Level Indicator Value_Years;
    define Education_Level / "Education Group" style(column)={width=35% font_weight=bold};
    define Indicator / "Health / Longevity Metric" style(column)={width=45%};
    define Value_Years / "Expected Years" format=5.1 style(column)={width=20% justification=r};
run;

ods text="^S={font_face='Arial' font_size=10pt font_weight=bold color=#000000}^nStrategic Conclusions for Dutch Healthcare & Prevention Policy:^n";
ods text="^S={font_face='Arial' font_size=8.5pt color=#27272a}1. Longevity Expansion: Total LE reaches 86.5 years, but 1.2 years of the gain will be lived with functional disability.^n";
ods text="^S={font_face='Arial' font_size=8.5pt color=#27272a}2. Multimorbidity Pressure: Over 4.3 million citizens will have 3 or more chronic conditions by 2050, necessitating integrated generalist care.^n";
ods text="^S={font_face='Arial' font_size=8.5pt color=#27272a}3. The Dementia Tsunami: With DALYs surging +146% to 346,300, dementia becomes the #1 national healthcare challenge.^n";
ods text="^S={font_face='Arial' font_size=8.5pt color=#27272a}4. Persistent Inequalities: Targeted prevention must address the 14.6-year healthy life expectancy gap across socioeconomic gradients.^n";

ods pdf close;
ods listing;
