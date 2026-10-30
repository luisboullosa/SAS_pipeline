# Dutch Public Health Foresight Study (VTV / PHFS): National Burden of Disease (DALYs)

This clinical programming and epidemiological analytics project models, calculates, and visualizes the disease burden for the Netherlands based on **Statistics Netherlands (CBS)** open data and the **2024 Dutch Burden of Disease Study (VTV / PHFS)**.

---

## 1. Academic Reference & Scientific Context

- **Study Title**: *"Dutch DALYs: the 2024 update of the Dutch Burden of disease study"*
- **Authors**: H. Hilderink, M. Plasmans, P. Eijsink, M. Buis, G. de Boer, R. Poos (National Institute for Public Health and the Environment [RIVM])
- **Publication**: *European Journal of Public Health*, Volume 35, Supplement 4, October 2025, Article `ckaf161.580`
- **Canonical Article URL**: [https://academic.oup.com/eurpub/article/35/Supplement_4/ckaf161.580/8303243](https://academic.oup.com/eurpub/article/35/Supplement_4/ckaf161.580/8303243)
- **DOI**: `10.1093/eurpub/ckaf161.580`

### Public Health Foresight Study (VTV) Scope
The Dutch Public Health Foresight Study (*Volksgezondheid Toekomst Verkenning* - VTV) is conducted quadrennially by RIVM to synthesize national health status, disease burden, demographic shifts, and healthcare demand:
- Synthesizes estimates for **over 120 diseases** and **100 risk factors** (smoking, overweight, alcohol, physical inactivity, air pollution).
- Incorporates revised disability weights, cause-specific mortality registers, and disease trajectories from 2022 through 2050.
- Highlights prominent growth in chronic degenerative diseases and youth mental health burdens.

---

## 2. Data Sources & Statistics Netherlands (`cbsodata`)

Data is ingested directly from the official **CBS Open Data Portal** via the Python [`cbsodata`](https://pypi.org/project/cbsodata/) library:

| CBS Table ID | Dutch Official Title | Extracted Variables / Metrics |
| :--- | :--- | :--- |
| `84067NED` | *Ziekenhuisopnamen en -patiënten; diagnose-indeling VTV* | Hospital admissions, patient counts, rates per 10k across 245 VTV diagnoses, sex, and age strata |
| `7052_95` | *Overledenen; belangrijke doodsoorzaken (korte lijst)* | Primary underlying cause of death counts by ICD-10 chapters, sex, and age |
| `71950ned` | *Gezonde levensverwachting; vanaf 1981* | Total life expectancy, healthy life expectancy, and disability-free life expectancy |

---

## 3. Epidemiological Framework: DALY Calculation

The pipeline implements the standard Global Burden of Disease (GBD) / RIVM formula:

$$\text{DALY} = \text{YLL} + \text{YLD}$$

1. **Years of Life Lost (YLL) — Mortality Burden**:
   $$\text{YLL} = \sum_{a, s, d} \left( \text{Deaths}_{a, s, d} \times \text{StandardLifeExpectancy}_a \right)$$
   Where standard life expectancy benchmarks aspirational survival at age of premature death.

2. **Years Lived with Disability (YLD) — Morbidity Burden**:
   $$\text{YLD} = \sum_{a, s, d} \left( \text{PrevalentCases}_{a, s, d} \times \text{DisabilityWeight}_d \right)$$
   Where disability weights ($DW \in [0, 1]$) reflect health-related quality of life reductions per RIVM 2024 parameters.

3. **Standardized Population Rates**:
   $$\text{DALY Rate per 10,000} = \left( \frac{\text{DALY}}{\text{Population}} \right) \times 10{,}000$$

---

## 4. Project Structure

```text
projects/dutch_phfs_burden_of_disease/
├── README.md                      # Project documentation and scientific context
├── cbs_client.py                  # CBS Open Data (cbsodata) extraction & cache client
├── vtv_daly_pipeline.py           # DALY calculation and rate standardization pipeline
├── run_project.py                 # End-to-end orchestration script
│
├── data/                          # Analysis datasets (Parquet columnar & CSV)
│   ├── cbs_vtv_hospital_morbidity.parquet
│   ├── cbs_cause_specific_mortality.parquet
│   ├── cbs_healthy_life_expectancy.parquet
│   ├── dutch_dalys_estimates.parquet
│   ├── dutch_dalys_estimates.csv
│   └── dutch_dalys_summary.csv
│
└── sas/                           # Publication-grade SAS programs
    ├── daly_macro.sas             # SAS macro library for DALY calculations
    └── phfs_nature_report.sas     # Nature Journal-style ODS PDF report generator
```

---

## 5. How to Run the Project

### Prerequisites
Activate the Python virtual environment:
```powershell
cd D:\Development\SAS\python
.\.venv\Scripts\activate
```

### Execution via Orchestration Script
Run the end-to-end Python pipeline and SAS reporting:
```powershell
python D:\Development\SAS\projects\dutch_phfs_burden_of_disease\run_project.py
```

### Direct Step-by-Step Execution
1. **Extract & Calculate DALYs**:
   ```powershell
   python D:\Development\SAS\projects\dutch_phfs_burden_of_disease\vtv_daly_pipeline.py
   ```
2. **Compile SAS Nature Report**:
   ```powershell
   # In SAS session or SAS Studio:
   %include "D:\Development\SAS\projects\dutch_phfs_burden_of_disease\sas\phfs_nature_report.sas";
   ```

---

## 6. Key Scientific Findings (2023 National Cohort)

According to our model output matching Hilderink et al. (2025):
1. **Neoplasms & Cancers** represent the leading contributor to premature mortality and overall DALYs in the Netherlands (>97% mortality component YLL).
2. **Cardiovascular & Circulatory Diseases** rank second, driven by coronary artery disease and heart failure.
3. **Major Depressive Disorders & Mental Health** generate high morbidity proportions (YLD) with concentrated burden in adolescent and young adult cohorts (ages 15–24 and 25–44).

---

## 7. RIVM VTV-2024 Trendscenario: Native SAS Replication (1990–2050)

All findings published in the official RIVM VTV-2024 Trendscenario ([https://www.volksgezondheidtoekomstverkenning.nl/vtv-2024/trendscenario](https://www.volksgezondheidtoekomstverkenning.nl/vtv-2024/trendscenario)) are recreated **entirely in native SAS**:

- **SAS Data Program**: [`sas/vtv_trendscenario_data.sas`](file:///D:/Development/SAS/projects/dutch_phfs_burden_of_disease/sas/vtv_trendscenario_data.sas)
  Compiles the official empirical time series (1990–2022) and projection vectors (2022–2050) across all 6 core themes:
  - Life expectancy & survival chances to milestone ages (65, 75, 85, 100)
  - Healthy life expectancy & disability-free longevity
  - Chronic disease counts by age cohort (0–64, 65–74, 75+)
  - Top 12 chronic diseases (2022 vs. 2050)
  - Disease burden shift (DALYs: 2022 vs. 2050)
  - Historical cause-of-death transition (Cardiovascular vs. Dementia vs. Cancers)
  - Socioeconomic educational health inequalities (Total LE vs. Healthy LE)
- **SAS Reporting Program**: [`sas/vtv_trendscenario_report.sas`](file:///D:/Development/SAS/projects/dutch_phfs_burden_of_disease/sas/vtv_trendscenario_report.sas)
  Generates a 5-page, 300-DPI publication vector PDF report (`VTV_2024_Trendscenario_Nature_Report.pdf`) featuring Nature Journal-style typography, unboxed SGPLOT graphics, executive summary, and linked audit tables.
- **Python Automation Runner**: [`run_vtv_trendscenario_sas.py`](file:///D:/Development/SAS/projects/dutch_phfs_burden_of_disease/run_vtv_trendscenario_sas.py)
  Automates the end-to-end execution through `saspy` and downloads the validated PDF report.

### Running the SAS Trendscenario Replication:
```powershell
python D:\Development\SAS\projects\dutch_phfs_burden_of_disease\run_vtv_trendscenario_sas.py
```
Or directly within SAS Studio / SAS ODA:
```sas
%include "D:\Development\SAS\projects\dutch_phfs_burden_of_disease\sas\vtv_trendscenario_report.sas";
```
