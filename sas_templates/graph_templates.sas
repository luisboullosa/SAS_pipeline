/*-----------------------------------------------------------------------------
 * SAS Graph Template Language (GTL) Definitions for Scientific Publishing
 * Templates: Nature_Scatter, Nature_MultiSeries, Ecology_TimeSeries, Ecology_BoxJitter
 * Compatible with SAS 9.4 / SAS ODA / PROC SGRENDER
 *----------------------------------------------------------------------------*/

proc template;
    /* 1. Nature Style Publication Scatterplot */
    define statgraph Nature_Scatter;
        begingraph / designwidth=6.8in designheight=4.2in;
            entrytitle "Figure 1 | " textattrs=(size=10.5pt weight=bold) entrytitle_var;
            entryfootnote halign=left textattrs=(size=7.5pt style=italic) footnote_var;
            layout overlay / 
                xaxisopts=(labelattrs=(size=8.5pt weight=bold) tickvalueattrs=(size=8pt) griddisplay=on)
                yaxisopts=(labelattrs=(size=8.5pt weight=bold) tickvalueattrs=(size=8pt) griddisplay=on);
                scatterplot x=x_var y=y1_var / name="grp1" legendlabel="Primary Cohort"
                    markerattrs=(color=gray symbol=circlefilled size=8px);
                scatterplot x=x_var y=y2_var / name="grp2" legendlabel="Secondary Cohort"
                    markerattrs=(color=black symbol=circlefilled size=8px);
                discretelegend "grp1" "grp2" / location=outside halign=center valign=top across=2 border=off;
            endlayout;
        endgraph;
    end;

    /* 2. Nature Style Multi-Cohort Longitudinal Series */
    define statgraph Nature_MultiSeries;
        begingraph / designwidth=6.8in designheight=4.2in;
            entrytitle "Figure 2 | " textattrs=(size=10.5pt weight=bold) entrytitle_var;
            layout overlay / 
                xaxisopts=(labelattrs=(size=8.5pt weight=bold) tickvalueattrs=(size=8pt) griddisplay=on)
                yaxisopts=(labelattrs=(size=8.5pt weight=bold) tickvalueattrs=(size=8pt) griddisplay=on);
                seriesplot x=x_var y=y_var / group=grp_var lineattrs=(thickness=1.8px) name="series";
                discretelegend "series" / location=outside halign=center valign=top across=3 border=off;
            endlayout;
        endgraph;
    end;

    /* 3. Ecology Journal Environmental Time Series */
    define statgraph Ecology_TimeSeries;
        begingraph / designwidth=6.8in designheight=4.2in;
            entrytitle "Figure | Environmental Monitoring Flux Time Series" textattrs=(size=10.5pt weight=bold);
            layout overlay / 
                xaxisopts=(labelattrs=(size=8.5pt weight=bold) tickvalueattrs=(size=8pt) griddisplay=on)
                yaxisopts=(labelattrs=(size=8.5pt weight=bold) tickvalueattrs=(size=8pt) griddisplay=on);
                bandplot x=x_var limitlower=ci_lower limitupper=ci_upper / 
                    fillattrs=(color=cxe8ece8 transparency=0.4) name="ci" legendlabel="95% Confidence Band";
                seriesplot x=x_var y=y_var / lineattrs=(color=cx2C5E3B thickness=2px) name="mean" legendlabel="Measured Trajectory";
                discretelegend "mean" "ci" / location=outside halign=center valign=top across=2 border=off;
            endlayout;
        endgraph;
    end;

    /* 4. Ecology Journal Distribution Boxplot with Observations */
    define statgraph Ecology_BoxJitter;
        begingraph / designwidth=6.8in designheight=4.2in;
            entrytitle "Figure | Ecological Parameter Variance & Distribution" textattrs=(size=10.5pt weight=bold);
            layout overlay / 
                xaxisopts=(labelattrs=(size=8.5pt weight=bold) tickvalueattrs=(size=8pt))
                yaxisopts=(labelattrs=(size=8.5pt weight=bold) tickvalueattrs=(size=8pt) griddisplay=on);
                boxplot x=category_var y=response_var / 
                    boxwidth=0.4 fillattrs=(color=cxf4f6f4) outlierattrs=(symbol=circle size=5px);
                scatterplot x=category_var y=response_var / 
                    jitter=auto markerattrs=(color=cx2C5E3B symbol=circlefilled size=4px transparency=0.5);
            endlayout;
        endgraph;
    end;
run;
