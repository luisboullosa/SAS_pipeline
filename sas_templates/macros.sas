/*-----------------------------------------------------------------------------
 * SAS Macros for Publication Graph Generation
 * Nature and Ecology Journal Standards
 *----------------------------------------------------------------------------*/

%macro nature_sgplot_scatter(data=, x=, y1=, y2=, label1=First Dose, label2=Second Dose, 
                             xlabel=Week, ylabel=Doses Administered, title=Figure 1 | Dose Scatterplot,
                             footnote=);
    ods graphics / reset width=6.8in height=4.2in noborder;
    proc sgplot data=&data;
        title "&title";
        %if %length(&footnote) > 0 %then %do;
            footnote halign=left italic "&footnote";
        %end;
        scatter x=&x y=&y1 / legendlabel="&label1" markerattrs=(color=gray symbol=circlefilled size=8);
        scatter x=&x y=&y2 / legendlabel="&label2" markerattrs=(color=black symbol=circlefilled size=8);
        xaxis label="&xlabel" valuesrotate=diagonal offsetmin=0.02 offsetmax=0.02 grid;
        yaxis label="&ylabel" grid;
        keylegend / location=outside position=top noborder;
    run;
%mend nature_sgplot_scatter;

%macro nature_sgplot_series(data=, x=, y=, group=, xlabel=Week, ylabel=Total Doses,
                            title=Figure 2 | Longitudinal Multi-Cohort Trend);
    ods graphics / reset width=6.8in height=4.2in noborder;
    proc sgplot data=&data;
        title "&title";
        series x=&x y=&y / group=&group lineattrs=(thickness=1.8);
        xaxis label="&xlabel" valuesrotate=diagonal offsetmin=0.02 offsetmax=0.02 grid;
        yaxis label="&ylabel" grid;
        keylegend / location=outside position=top across=3 noborder;
    run;
%mend nature_sgplot_series;

%macro ecology_sgplot_series(data=, x=, y=, group=, xlabel=Week, ylabel=Measurements,
                             title=Figure | Ecological Parameter Time Series);
    ods graphics / reset width=6.8in height=4.2in noborder;
    proc sgplot data=&data;
        title "&title";
        series x=&x y=&y / group=&group lineattrs=(thickness=2);
        xaxis label="&xlabel" valuesrotate=diagonal offsetmin=0.02 offsetmax=0.02 grid;
        yaxis label="&ylabel" grid;
        keylegend / location=outside position=top across=3 noborder;
    run;
%mend ecology_sgplot_series;
