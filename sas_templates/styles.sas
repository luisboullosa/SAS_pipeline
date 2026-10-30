/*-----------------------------------------------------------------------------
 * SAS Graph Style Templates for Scientific Publishing
 * Styles: NatureJournal, EcologyJournal
 * Compatible with SAS 9.4 / SAS ODA / ODS Graphics (300 DPI)
 *----------------------------------------------------------------------------*/

proc template;
    /* 1. Nature Journal Publication Style */
    define style styles.NatureJournal;
        parent = styles.listing;
        class GraphFonts /
            'GraphTitleFont'    = ("Arial, Helvetica, sans-serif", 10.5pt, bold)
            'GraphLabelFont'    = ("Arial, Helvetica, sans-serif", 9pt, bold)
            'GraphValueFont'    = ("Arial, Helvetica, sans-serif", 8pt)
            'GraphDataFont'     = ("Arial, Helvetica, sans-serif", 7.5pt)
            'GraphFootnoteFont' = ("Arial, Helvetica, sans-serif", 7.5pt, italic);
        class GraphColors /
            'gaxis' = cx1A1A1A
            'ggrid' = cxebebeb
            'gback' = cxffffff;
        class GraphWalls /
            frameborder = off
            backgroundcolor = cxffffff;
        class GraphDataDefault /
            markersize = 7px
            linethickness = 1.5px;
        /* Nature Classic Color Palette */
        class GraphData1 / contrastcolor=cx1A1A1A color=cx1A1A1A; /* Near Black */
        class GraphData2 / contrastcolor=cx737373 color=cx737373; /* Slate Gray */
        class GraphData3 / contrastcolor=cxE64B35 color=cxE64B35; /* Nature Coral Red */
        class GraphData4 / contrastcolor=cx00A087 color=cx00A087; /* Nature Teal */
        class GraphData5 / contrastcolor=cx3C5488 color=cx3C5488; /* Nature Navy */
        class GraphData6 / contrastcolor=cxF39B7F color=cxF39B7F; /* Soft Salmon */
        class GraphData7 / contrastcolor=cx8491B4 color=cx8491B4; /* Soft Indigo */
        class GraphData8 / contrastcolor=cx91D1C2 color=cx91D1C2; /* Pale Sage */
    end;

    /* 2. Ecology Journal Publication Style */
    define style styles.EcologyJournal;
        parent = styles.listing;
        class GraphFonts /
            'GraphTitleFont'    = ("Arial, Helvetica, sans-serif", 10.5pt, bold)
            'GraphLabelFont'    = ("Arial, Helvetica, sans-serif", 9pt, bold)
            'GraphValueFont'    = ("Arial, Helvetica, sans-serif", 8pt)
            'GraphDataFont'     = ("Arial, Helvetica, sans-serif", 7.5pt)
            'GraphFootnoteFont' = ("Arial, Helvetica, sans-serif", 7.5pt, italic);
        class GraphColors /
            'gaxis' = cx243527
            'ggrid' = cxe8ede8
            'gback' = cxffffff;
        class GraphWalls /
            frameborder = off
            backgroundcolor = cxffffff;
        class GraphDataDefault /
            markersize = 7px
            linethickness = 1.5px;
        /* Ecology / Environmental Color Palette */
        class GraphData1 / contrastcolor=cx2C5E3B color=cx2C5E3B; /* Deep Forest Green */
        class GraphData2 / contrastcolor=cx8C6239 color=cx8C6239; /* Soil Brown */
        class GraphData3 / contrastcolor=cx2B547E color=cx2B547E; /* Catchment Blue */
        class GraphData4 / contrastcolor=cxD4A017 color=cxD4A017; /* Canopy Amber */
        class GraphData5 / contrastcolor=cx556B2F color=cx556B2F; /* Dark Olive */
        class GraphData6 / contrastcolor=cx708090 color=cx708090; /* Mineral Slate */
    end;
run;
