# Determinants of Global Life Expectancy: A General Linear Model Analysis

An epidemiological and health-economics showcase project implementing a General Linear Model (GLM) / ANCOVA in native SAS via `saspy`, modeling national life expectancy determinants using indicators from the **World Health Organization (WHO)** and the **World Bank**.

---

## 1. Scientific Overview & Methodology

This project evaluates the relationship between national macroeconomic indicators, healthcare resource allocation, and population life expectancy at birth across diverse global economies.

### Statistical Specification
- **Response Variable ($Y$)**: `Life_Expectancy` (at birth, years)
- **Continuous Covariates**:
  - $\ln(\text{GDP})$ (`Log_GDP`): Natural logarithm of per-capita GDP (modeling the concave Preston curve where marginal health gains diminish at higher income levels).
  - `Health_Expenditure_Pct`: Current health expenditure as a percentage of gross domestic product.
  - `Urbanization_Pct`: Percentage of national population living in urban agglomerations.
- **Categorical Factor ($X_{\text{class}}$)**:
  - `Region`: Continental/geographical macro-region (Europe, Americas, Asia-Pacific, Africa, Middle East).
- **Hypothesis Testing**:
  - ANCOVA with Type I and Type III Sum of Squares (`PROC GLM`) to evaluate main effects and regional adjustments.
  - Parameter estimation with robust 95% confidence intervals and $t$-tests against the null hypothesis ($\beta_i = 0$).
  - Residual diagnostics (`PROC UNIVARIATE`) verifying normality assumptions via Shapiro-Wilk statistics and Q-Q plots.
  - Multicollinearity assessment (`PROC REG / VIF TOL COLLIN`) ensuring parameter stability across regressors.

---

## 2. Project Directory Structure

```text
projects/longevity_linear_model/
├── data/
│   ├── global_longevity_gdp.csv                  # Multi-country longitudinal benchmark dataset
│   └── Life_Expectancy_Linear_Model_Report.pdf   # Publication-quality SAS ODS PDF report
├── life_expectancy_glm.sas                       # Native SAS GLM, REG & ODS PDF implementation
├── run_model.py                                  # Python orchestration script via saspy
└── README.md                                     # Methodology & documentation
```

---

## 3. Data Dictionary

| Variable Name | Type | Description | Source |
| :--- | :--- | :--- | :--- |
| `Country_Code` | Character (3) | ISO 3166-1 alpha-3 international country code | ISO / World Bank |
| `Country_Name` | Character (30) | Standard country English designation | WHO / World Bank |
| `Region` | Character (25) | Macro-geographical region | UN / World Bank |
| `Year` | Numeric | Observation calendar year (2023 baseline) | WHO GHO |
| `Life_Expectancy` | Numeric | Life expectancy at birth in years (both sexes) | WHO GHO (`WHOSIS_000001`) |
| `GDP_Per_Capita` | Numeric | GDP per capita (constant 2015 USD) | World Bank (`NY.GDP.PCAP.CD`) |
| `Log_GDP` | Numeric | Natural logarithm of per-capita GDP: $\ln(\text{GDP})$ | Derived |
| `Health_Expenditure_Pct` | Numeric | Healthcare expenditure (% of GDP) | WHO Global Health Expenditure |
| `Urbanization_Pct` | Numeric | Urban population (% of total) | World Bank Urban Development |

---

## 4. Execution Guide

### Prerequisites
1. Python environment activated (with `saspy` and `pypdf` installed).
2. Active SAS OnDemand for Academics (ODA) profile configured in `~/_authinfo`.

### Running via Python Orchestrator
```bash
python projects/longevity_linear_model/run_model.py
```

The script will:
1. Connect to the remote SAS session via `saspy`.
2. Upload `global_longevity_gdp.csv` to the session's temporary `WORK` library.
3. Submit `life_expectancy_glm.sas`.
4. Pull back model goodness-of-fit, parameter estimates, and ANOVA tables into Pandas DataFrames.
5. Download and verify the generated publication PDF report (`Life_Expectancy_Linear_Model_Report.pdf`).

### Running Directly in SAS Studio
Open `life_expectancy_glm.sas` in SAS Studio (OnDemand for Academics or local SAS 9.4+), and click **Run**. The script will automatically fall back to its embedded self-contained datalines if external files are not staged, compiling the ODS PDF directly to your session `WORK` library.

