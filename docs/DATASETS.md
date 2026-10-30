# Scientific & Clinical Dataset Directory & Access Guide

This document provides complete technical specifications, access protocols, schemas, and integration code for all **16 scientific and clinical datasets** supported by the SAS Clinical & Epidemiological Analytics Platform.

---

## Table of Contents

1. [Dataset Registry Overview](#1-dataset-registry-overview)
2. [Authentication & Secrets Configuration](#2-authentication--secrets-configuration)
3. [Scientific Dataset Catalog & Access Protocols](#3-scientific-dataset-catalog--access-protocols)
   - [3.1 ECDC COVID-19 Vaccine Surveillance Tracker](#31-ecdc-covid-19-vaccine-surveillance-tracker)
   - [3.2 Dutch Burden of Disease & Environmental Mobility (RDW SODA 3)](#32-dutch-burden-of-disease--environmental-mobility-rdw-soda-3)
   - [3.3 Dutch Public Health Foresight Study: DALYs (CBS 84067NED)](#33-dutch-public-health-foresight-study-dalys--disease-burden-cbs-84067ned)
   - [3.4 Dutch Lifestyle & Determinants Monitor (CBS 85464NED)](#34-dutch-lifestyle--health-determinants-monitor-cbs-85464ned)
   - [3.5 Dutch National Population Forecast 2022–2070 (CBS 85323NED)](#35-dutch-population-forecast-20222070-cbs-85323ned)
   - [3.6 WHO Global Health Observatory Longevity Benchmarks](#36-who-global-health-observatory-longitudinal-life-expectancy-benchmarks)
   - [3.7 UNEP GEMS/Water Global Freshwater Quality Archive](#37-unep-gemswater-global-freshwater-quality-archive)
   - [3.8 FOTO-NL Surface Water Chemical Pollution Monitoring](#38-foto-nl-surface-water-chemical-pollution-monitoring)
   - [3.9 SA-FARI Open Wildlife Video & SAM3 Segmentation](#39-sa-fari-open-wildlife-video--sam3-segmentation)
   - [3.10 Loobos Forest Ecosystem Tower Micrometeorology & Fluxes](#310-loobos-forest-ecosystem-tower-micrometeorology--fluxes)
   - [3.11 ICP IM Long-Term Air Pollution Catchment Ecology](#311-icp-im-long-term-air-pollution-catchment-ecology)
   - [3.12 Health-RI National Dutch Health Data Catalogue](#312-health-ri-national-dutch-health-data-catalogue)
   - [3.13 Mendeley Cognitive & Behavioral Neurodiversity Profiles](#313-mendeley-cognitive--behavioral-neurodiversity-profiles)
   - [3.14 SHARE-MH Scottish Mental Health Research Register](#314-share-mh-scottish-mental-health-research-register)
   - [3.15 LISS Panel Longitudinal Internet Studies (Netherlands)](#315-liss-panel-longitudinal-internet-studies-netherlands)
   - [3.16 Netherlands Twin Register (NTR) Longitudinal Cohort](#316-netherlands-twin-register-ntr-longitudinal-cohort)
4. [Scientific Dataset Sets (Bundles)](#4-scientific-dataset-sets-bundles)
5. [High-Speed Parquet Caching & Dual-Store Architecture](#5-high-speed-parquet-caching--dual-store-architecture)
6. [Multi-Table Zip Archive Packages](#6-multi-table-zip-archive-packages)
7. [REST API Access Reference](#7-rest-api-access-reference)

---

## 1. Dataset Registry Overview

| Dataset ID | Discipline / Domain | Primary Provider | Scale & Scope | Access Protocol | Local Cache Format |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `ecdc-covid-vaccine` | Public Health & Epidemiology | ECDC / data.europa.eu | 813,367 rows (Weekly doses) | Direct HTTP CSV | Parquet Columnar |
| `dutch-dalys-pmc` | Mobility & Public Sector Open Data | RDW (Dienst Wegverkeer) | Live Stream (102 variables) | SODA 3 Views Query API | SODA 3 Parquet |
| `cbs-vtv-phfs` | Public Health & Burden of Disease | RIVM & CBS (`cbsodata`) | 1,536 Stratified DALY Estimates | CBS OData API / `cbsodata` | VTV DALY Parquet |
| `cbs-vtv-determinants` | Public Health & Behavioral Epidemiology | CBS & RIVM (`cbsodata`) | 720 Stratified Cohorts (63 vars) | CBS OData API (Table `85464NED`) | Columnar Parquet |
| `cbs-population-forecast` | Demography & Actuarial Epidemiology | Statistics Netherlands (`cbsodata`) | 240 Forecast Intervals (2022–2070) | CBS OData API (Table `85323NED`) | Columnar Parquet |
| `who-gho-odata` | Global Health Statistics & Longevity | WHO & World Bank Open Data | 396 Benchmark Years (1960–2024) | REST OData / World Bank API | Columnar Parquet |
| `unep-gems-water` | Global Hydrology & Water Quality | UNEP / ICWRGC & BfG / Zenodo | 50M+ rows (22,982 stations) | Zenodo REST / ZIP Package | Multi-Table Parquet |
| `foto-nl-water-pollution` | Environmental Toxicology | RIVM & Water Boards / Zenodo | 35.7M clean (51.5M raw) | Zenodo REST / Harmonized ZIP | Multi-Table Parquet |
| `sa-fari-wildlife` | Biodiversity & Vision AI | Conservation X Labs & Meta | 11,000+ videos (99 species) | HTTP / SAM3 Video Archive | Multi-Table Parquet |
| `loobos-flux-meteorology` | Carbon Cycle & Micrometeorology | Copernicus ESSD | 25-Year 30-min tower fluxes | Copernicus ESSD Archive | Parquet Metadata |
| `icp-im-air-pollution` | Atmospheric Ecology | Swedish Research Council | Multi-Decadal European basins | researchdata.se OAI-PMH | Parquet Metadata |
| `health-ri-catalogue` | Life Sciences Infrastructure | Health-RI Netherlands | National biobank registry | HealthData.nl Registry Index | Parquet Metadata |
| `mendeley-neurodiversity` | Educational & Cognitive Psychology | Mendeley Data | 420 subjects, 12 trait axes | Mendeley Data Direct Link | Parquet Metadata |
| `edinburgh-share-mh` | Psychiatric Epidemiology | Univ. of Edinburgh / NHS | Scottish psychiatric register | Edinburgh DataShare Archive | Parquet Metadata |
| `liss-panel-nl` | Longitudinal Population Health | Centerdata & Tilburg Univ. | 5,000 households / 7.5K ind. | LISS Data Portal | Parquet Metadata |
| `openneuroscience-ntr` | Behavioral & Twin Genetics | VU Amsterdam & Open Neuroscience | 120,000+ twin participants | Open Neuroscience Directory | Parquet Metadata |

---

## 2. Authentication & Secrets Configuration

All external API keys and authentication tokens are strictly segregated from code and managed through internal secret files.

### 2.1 File Location & Security Standard
- **Path**: `.env` (or `.secrets/.auth.txt`)
- **Exclusion**: Tracked in `.gitignore` (`.secrets/`, `*.auth.txt`, `.env*`).
- **Policy**: Credentials must **never** be logged, printed to console, or returned in HTTP response payloads.

### 2.2 Supported Credentials
```text
# Example .env or .secrets/.auth.txt:
API_KEY_ID=your_socrata_key_id
RDW_API_KEY_SECRET=your_socrata_key_secret
ZENODO_API_TOKEN=your_zenodo_bearer_token
```

### 2.3 Programmatic Ingestion (`python/dashboard/socrata_client.py`)
```python
from python.dashboard.socrata_client import load_socrata_credentials, is_socrata_configured

# Safely load credentials without exposure
creds = load_socrata_credentials()
print(f"Socrata configured: {is_socrata_configured()}")
```

---

## 3. Scientific Dataset Catalog & Access Protocols

---

### 3.1 ECDC COVID-19 Vaccine Surveillance Tracker
- **Dataset ID**: `ecdc-covid-vaccine`
- **Discipline**: Epidemiology & Infectious Disease Surveillance
- **Provider**: European Centre for Disease Prevention and Control (ECDC)
- **Source URL**: `https://opendata.ecdc.europa.eu/covid19/vaccine_tracker/csv/data.csv`
- **Scale**: 813,367 rows (Updated weekly, 2020–2024)
- **Access Protocol**: Direct HTTP `GET` streaming CSV.
- **Core Schema (18 Variables)**:
  - `Var #1`: `YearWeekISO` — ISO 8601 Calendar Year & Week (e.g., `2021-W15`)
  - `Var #2`: `FirstDose` — Count of First Vaccine Doses Administered
  - `Var #3`: `SecondDose` — Count of Second Vaccine Doses Administered
  - `Var #4`: `DoseAdditional1` — Count of First Booster / Additional Doses
  - `Var #6`: `UnknownDose` — Unclassified Vaccine Dose Counts
  - `Var #8`: `NumberDosesReceived` — Cumulative Inflow of Physical Vaccine Doses
  - `Var #10`: `ReportingCountry` — ISO 3166-1 alpha-2 Member State Identifier
  - `Var #12`: `TargetGroup` — Stratified Age Cohort or Clinical Target Group
  - `Var #13`: `Vaccine` — Biological Vaccine Product Designation
  - `Var #14`: `Population` — National Demographic Denominator
- **How to Access via Python**:
  ```python
  from python.dashboard.cache_manager import DatasetCacheManager
  cache_mgr = DatasetCacheManager()
  df = cache_mgr.load_dataframe('ecdc-covid-vaccine')
  ```
- **SAS SQL Example**:
  ```sas
  proc sql;
      select ReportingCountry, sum(FirstDose) as TotalFirstDoses format=comma12.
      from work.covid_data
      where TargetGroup = 'Age60_69'
      group by ReportingCountry
      order by TotalFirstDoses desc;
  quit;
  ```

---

### 3.2 Dutch Open Vehicle Fleet Registry (RDW SODA 3 API Showcase)
- **Dataset ID**: `dutch-dalys-pmc` (Identifier retained for client backwards-compatibility)
- **Discipline**: Public Sector Mobility & Fleet Open Data
- **Provider**: RDW (Dienst Wegverkeer, Open Data RDW)
- **Primary Endpoint (SODA 3 Views Query API)**:
  ```
  https://opendata.rdw.nl/api/v3/views/2snn-6yr9/query.csv
  ```
- **Legacy Fallback Endpoint (SODA 2.x)**:
  ```
  https://opendata.rdw.nl/resource/2snn-6yr9.csv
  ```
- **Scale**: Real-time streaming database of the entire Netherlands motor vehicle fleet; over 15 million registrations, 102 variables.
- **Access Protocol**: Socrata Open Data API (SODA 3) with HTTP Basic Authentication (`Authorization: Basic <base64(API_KEY_ID:RDW_API_KEY_SECRET)>`).
- **Query Syntax**: Standard SQL expressions via `query` parameter:
  ```sql
  SELECT kenteken, voertuigsoort, merk, handelsbenaming, bruto_bpm, zuinigheidsclassificatie 
  WHERE voertuigsoort = 'Personenauto' 
  ORDER BY datum_eerste_toelating DESC 
  LIMIT 5000
  ```
- **Core Schema (Sample of 102 Variables)**:
  - `Var #1`: `kenteken` — Vehicle Registration License Plate Identifier
  - `Var #2`: `voertuigsoort` — Vehicle Functional Category / Classification
  - `Var #3`: `merk` — Vehicle Manufacturer / Brand Designation
  - `Var #4`: `handelsbenaming` — Commercial Trade / Model Designation
  - `Var #5`: `vervaldatum_apk` — Periodic Technical Safety Inspection Expiry (APK)
  - `Var #7`: `bruto_bpm` — Gross Private Motor Vehicle Tax (EUR BPM)
  - `Var #14`: `massa_ledig_voertuig` — Unladen Curb Weight (kg)
  - `Var #15`: `toegestane_maximum_massa_voertuig` — Permissible Maximum Gross Weight (kg)
  - `Var #36`: `zuinigheidsclassificatie` — Energy Efficiency & Carbon Emissions Label
  - `Var #95`: `api_gekentekende_voertuigen_brandstof` — Fuel & Environmental Emissions SODA Endpoint
- **How to Access via Python (`socrata_client.py`)**:
  ```python
  from python.dashboard.socrata_client import fetch_socrata_dataset

  df, raw_bytes = fetch_socrata_dataset(
      resource_url="https://opendata.rdw.nl/api/v3/views/2snn-6yr9/query.csv",
      where="voertuigsoort = 'Personenauto'",
      limit=1000
  )
  print(df[['kenteken', 'merk', 'handelsbenaming', 'bruto_bpm']].head())
  ```

---

### 3.3 UNEP GEMS/Water Global Freshwater Quality Archive
- **Dataset ID**: `unep-gems-water`
- **Discipline**: Global Hydrology, Hydrochemistry & Water Resource Monitoring
- **Provider**: United Nations Environment Programme (UNEP) / International Centre for Water Resources and Global Change (ICWRGC) / Federal Institute of Hydrology (BfG)
- **Source URL**: `https://zenodo.org/records/18459694`
- **Package Archive**: `GFQA_v3.zip` (Zenodo DOI: `10.5281/zenodo.18459694`)
- **Scale**: 50,000,000+ water quality observations across 22,982 monitoring stations in 42 UN Member States (1906–2024).
- **Access Protocol**: Zenodo REST API (`https://zenodo.org/api/records/18459694`) and local unzipped package parsing.
- **Unpacked Multi-Table Members**:
  1. `stations_catalogue.csv` — Station metadata (WGS-84 coordinates, catchment area, river basin).
  2. `gfqa_water_quality_measurements.csv` — Primary observations (nitrates, phosphates, pH, heavy metals).
  3. `parameters_codebook.csv` — GEMS parameter taxonomy (622 chemical and physical indicators).
- **Core Schema**:
  - `station_id` — Global Hydrological Station Identifier
  - `sample_date` — Sampling Collection Timestamp (ISO 8601)
  - `nitrate_mg_l` — Nitrate Concentration (mg/L NO3-)
  - `phosphate_mg_l` — Total Phosphate Concentration (mg/L PO4-P)
  - `ph_value` — Hydrogen-Ion Activity (pH Units)
  - `dissolved_oxygen_mg_l` — Dissolved Oxygen (mg/L O2)
- **How to Access Member Tables in Python**:
  ```python
  from python.dashboard.cache_manager import DatasetCacheManager
  cache_mgr = DatasetCacheManager()
  
  # Discover and inspect unzipped archive members
  members = cache_mgr.get_package_members('unep-gems-water')
  print([m['file_name'] for m in members])
  
  # Load specific member table
  df_stations = cache_mgr.load_member_dataframe('unep-gems-water', 'stations_catalogue.csv')
  ```

---

### 3.4 FOTO-NL Surface Water Chemical Pollution Monitoring
- **Dataset ID**: `foto-nl-water-pollution`
- **Discipline**: Environmental Toxicology & Aquatic Chemistry
- **Provider**: RIVM & 21 Regional Dutch Water Boards / Zenodo
- **Source URL**: `https://zenodo.org/records/19494234`
- **Scale**: 35,756,662 cleaned measurements (51.5M raw entries) spanning 1954–2020 across the Rhine, Meuse, and national catchment networks.
- **Access Protocol**: Zenodo REST API and multi-table harmonized Parquet store.
- **Key Variables**:
  - `locatie_code` — Monitoring Catchment Location Code
  - `monster_datum` — Sample Collection Date
  - `parameter_cas` — Chemical Abstracts Service Registry Number (CAS RN)
  - `waarde` — Numeric Measurement Value
  - `eenheid` — Unit of Measurement (ug/L, mg/L)
  - `detectiegrens_flag` — Pretreatment and Below-LOD Censoring Flag

---

### 3.5 SA-FARI Open Wildlife Video & SAM3 Segmentation
- **Dataset ID**: `sa-fari-wildlife`
- **Discipline**: Wildlife Ecology, Conservation & Computer Vision AI
- **Provider**: Conservation X Labs, Meta AI (Segment Anything Model 3)
- **Source URL**: `http://conservationxlabs.com/sa-fari`
- **Scale**: 11,000+ camera trap video sequences, 99 wild mammal and bird species, dense spatiotemporal masks.
- **Access Protocol**: Multi-member metadata package archive (`sa_fari_metadata_package.zip`).
- **Unpacked Multi-Table Members**:
  1. `species_catalogue.csv` — 99 species with scientific nomenclature, vernacular names, and IUCN Red List statuses.
  2. `camera_trap_deployments.csv` — GPS locations, camera trap hardware types, and habitat biomes.
  3. `video_annotations_sam3.csv` — Frame-by-frame SAM3 segmentation mask references, bounding boxes, and tracklets.
- **Core Schema**:
  - `species_id` — Taxonomic Species Identifier
  - `scientific_name` — Binomial Scientific Nomenclature
  - `common_name` — Vernacular English Name
  - `iucn_status` — IUCN Red List Conservation Status
  - `camera_trap_id` — Camera Trap Hardware Identifier
  - `duration_sec` — Video Clip Duration (Seconds)
  - `animal_tracklets` — Temporal Multi-Frame Trajectory Tracklets

---

### 3.6 Loobos Forest Ecosystem Tower Micrometeorology & Fluxes
- **Dataset ID**: `loobos-flux-meteorology`
- **Discipline**: Terrestrial Carbon Dynamics & Micrometeorology
- **Provider**: Earth System Science Data (Copernicus ESSD)
- **Source URL**: `https://essd.copernicus.org/articles/18/2023/2026/`
- **Scale**: Continuous 30-minute eddy-covariance records over 25 years (1996–2021) above a temperate Scots pine forest (Pinus sylvestris).
- **Access Protocol**: ESSD open-access repository DOI metadata and NetCDF/ASCII archive access.
- **Core Physical Quantities**:
  - `NEE` — Net Ecosystem Exchange of CO2 (umol / m^2 / s)
  - `H` — Sensible Heat Flux (W / m^2)
  - `LE` — Latent Heat Flux (W / m^2)
  - `SW_IN` — Incoming Shortwave Solar Radiation (W / m^2)
  - `VPD` — Vapor Pressure Deficit (hPa)

---

### 3.7 ICP IM Long-Term Air Pollution Catchment Ecology
- **Dataset ID**: `icp-im-air-pollution`
- **Discipline**: Atmospheric Pollution & Watershed Biogeochemistry
- **Provider**: Swedish Research Council / researchdata.se
- **Source URL**: `https://researchdata.se/en/catalogue/dataset/2024-180`
- **Scale**: Catchment-scale long-term ecosystem monitoring under the UNECE Convention on Long-range Transboundary Air Pollution (CLRTAP).
- **Access Protocol**: OAI-PMH harvest and metadata catalog indexing.
- **Measurements**: Acid deposition, sulfur/nitrogen compounds, soil water chemistry, vegetation biodiversity shifts.

---

### 3.8 Health-RI National Dutch Health Data Catalogue
- **Dataset ID**: `health-ri-catalogue`
- **Discipline**: Biomedical Research & Life Sciences Infrastructure
- **Provider**: Health-RI Netherlands
- **Source URL**: `https://www.healthdata.nl/en/data-catalogue/about-catalogue`
- **Scale**: National federated directory of Dutch clinical registries, cohort studies, and biobanks.
- **Access Protocol**: Metadata index for secondary biomedical and epidemiological research.

---

### 3.9 Mendeley Cognitive & Behavioral Neurodiversity Profiles
- **Dataset ID**: `mendeley-neurodiversity`
- **Discipline**: Educational Psychology & Cognitive Neurodiversity
- **Provider**: Mendeley Data / Dar Deen, Deen MOHD
- **Source URL**: `https://data.mendeley.com/datasets/22mw357f2y/1`
- **Scale**: 420 adolescent students (ages 10–18), 12 neurodivergent trait domains.
- **Access Protocol**: Mendeley Data repository Direct API.
- **Core Schema**: Anonymized scoring across sensory processing, attentional switching, executive function, working memory, and social communication scales.

---

### 3.10 SHARE-MH Scottish Mental Health Research Register
- **Dataset ID**: `edinburgh-share-mh`
- **Discipline**: Psychiatric Epidemiology & Health Informatics
- **Provider**: University of Edinburgh / Centre for Clinical Brain Sciences / NHS Scotland
- **Source URL**: `https://datashare.ed.ac.uk/items/a4b6ea33-6234-424e-988d-ee3329903a1a`
- **Scale**: Validated psychiatric survey cohorts linkable to longitudinal NHS electronic health records.
- **Access Protocol**: Edinburgh DataShare repository catalog.

---

### 3.11 LISS Panel Longitudinal Internet Studies (Netherlands)
- **Dataset ID**: `liss-panel-nl`
- **Discipline**: Socio-Economics, Demography & Population Health
- **Provider**: Centerdata & Tilburg University
- **Source URL**: `https://www.lissdata.nl/`
- **Scale**: 5,000 households (7,500 individuals) tracked continuously via monthly probability-based online survey waves since 2007.
- **Access Protocol**: LISS Data Archive authenticated access.

---

### 3.12 Netherlands Twin Register (NTR) Longitudinal Cohort
- **Dataset ID**: `openneuroscience-ntr`
- **Discipline**: Behavioral Genetics, Neuroepidemiology & Gene-Environment Interaction
- **Provider**: Vrije Universiteit Amsterdam & Open Neuroscience
- **Source URL**: `https://openneuroscience.org/Actors/NTR`
- **Scale**: Over 120,000 twins and relatives followed longitudinally from birth through adulthood with extensive biobanking.
- **Access Protocol**: Open Neuroscience data portal and scientific collaboration request.

---

### 3.13 Dutch Public Health Foresight Study: DALYs & Disease Burden (RIVM / CBS)
- **Dataset ID**: `cbs-vtv-phfs`
- **Discipline**: Public Health, Burden of Disease & Clinical Epidemiology
- **Primary Provider**: RIVM & Statistics Netherlands (Centraal Bureau voor de Statistiek - CBS)
- **Scientific Reference**: Hilderink et al., *"Dutch DALYs: the 2024 update of the Dutch Burden of disease study"*, *European Journal of Public Health*, Vol. 35, Suppl. 4, Oct 2025, `ckaf161.580`, [doi: 10.1093/eurpub/ckaf161.580](https://academic.oup.com/eurpub/article/35/Supplement_4/ckaf161.580/8303243).
- **Access Protocol**: Direct Python integration via [`cbsodata`](https://pypi.org/project/cbsodata/) library querying CBS OData API v3/v4.
- **Core CBS Source Tables**:
  - `84067NED`: *Ziekenhuisopnamen en -patiënten; diagnose-indeling VTV* (245 diagnoses, admission types, sex, age strata)
  - `7052_95`: *Overledenen; belangrijke doodsoorzaken (korte lijst)* (ICD-10 cause-specific mortality)
  - `71950ned`: *Gezonde levensverwachting; vanaf 1981* (Total, disability-free, and healthy life expectancy)
- **Calculated Epidemiological Variables (N=16 Priority Disease Categories)**:
  - `DALY`: Disability-Adjusted Life Years ($\text{DALY} = \text{YLL} + \text{YLD}$)
  - `YLL`: Years of Life Lost ($\text{Deaths} \times \text{ResidualLifeExpectancy}$)
  - `YLD`: Years Lived with Disability ($\text{Cases} \times \text{DisabilityWeight}$)
  - `DALY_Rate_Per10k`: DALY rate per 10,000 inhabitants
  - `YLL_Pct` / `YLD_Pct`: Mortality vs. disability component contribution (%)
  - `Disease_Name`: Cancers, Cardiovascular, Mental Health, Respiratory, Diabetes, Musculoskeletal
  - `Age_Stratum`: Standardized age intervals (`<15`, `15-24`, `25-44`, `45-64`, `65-74`, `75+`, `Total`)
  - `Gender`: `Both Sexes`, `Male`, `Female`
  - `Year`: 2020–2023 surveillance period
- **Dedicated Project**: [`projects/dutch_phfs_burden_of_disease/`](file:///D:/Development/SAS/projects/dutch_phfs_burden_of_disease/)
  - Pipeline: `vtv_daly_pipeline.py`
  - Client: `cbs_client.py`
  - SAS Macros: `sas/daly_macro.sas`
  - Nature Journal Report: `sas/phfs_nature_report.sas`
  - Orchestration: `run_project.py`

---

### 3.14 Dutch Lifestyle & Health Determinants Monitor (CBS 85464NED)
- **Dataset ID**: `cbs-vtv-determinants`
- **Discipline**: Public Health & Behavioral Epidemiology
- **Provider**: Statistics Netherlands (CBS) & RIVM Leefstijlmonitor
- **Table ID**: `85464NED` (*Leefstijl; geslacht, leeftijd, persoonskenmerken*)
- **Scale**: 720 Stratified Multi-Year Cohorts across 63 variables (2014–2023)
- **Access Protocol**: CBS Open Data REST API via Python `cbsodata`.
- **Core Indicators**:
  - `Rokers_1`: Current smoking prevalence (%)
  - `DagelijksRokersOnderBevolking_4`: Daily smoking prevalence (%)
  - `ESigaret12JaarOfOuder_5`: E-cigarette and vaping prevalence (%)
  - `Drinkers_6`: Alcohol drinkers in adult population (%)
  - `OvermatigeDrinkersOnderDrinkers_10`: Excessive alcohol consumption (%)
  - `RichtlijnAlcoholgebruik12JrOfOuder_13`: Health Council alcohol guideline compliance (%)
  - Stratification: Sex (`Geslacht`), Age (`Leeftijd`), Educational Attainment (`KenmerkenVanPersonen`)

---

### 3.15 Dutch National Population Forecast 2022–2070 (CBS 85323NED)
- **Dataset ID**: `cbs-population-forecast`
- **Discipline**: Demography & Actuarial Longevity Modeling
- **Provider**: Statistics Netherlands (CBS Bevolkingsprognose)
- **Table ID**: `85323NED` (*Prognose bevolking; kerncijfers, 2022-2070*)
- **Scale**: 240 Forecast Intervals (2022–2070) with 67% and 95% confidence bounds
- **Access Protocol**: CBS Open Data REST API via Python `cbsodata`.
- **Core Indicators**:
  - `BevolkingOp1Januari_1`: Total projected population count
  - `k_0Tot20Jaar_2`: Youth cohort count (0–20 years)
  - `k_20Tot65Jaar_3`: Working age cohort count (20–65 years)
  - `k_65JaarEnOuder_4`: Senior cohort count (65+ years)
  - `TotaleDruk_8`: Total demographic dependency ratio (%)
  - `GroeneDruk_9`: Youth dependency ratio (%)
  - `GrijzeDruk_10`: Old-age dependency ratio (%)

---

### 3.16 WHO Global Health Observatory: Longitudinal Life Expectancy Benchmarks
- **Dataset ID**: `who-gho-odata`
- **Discipline**: Global Health Statistics & Comparative Longevity
- **Provider**: World Health Organization (WHO) & World Bank Open Data
- **Endpoint**: `https://ghoapi.azureedge.net/api/WHOSIS_000001` & World Bank API
- **Scale**: 396 Multi-Country Benchmark Years (1960–2024)
- **Access Protocol**: REST API JSON streaming with high-speed caching.
- **Core Indicators**:
  - `Country_Code`: ISO Alpha-3 identifier (`NLD`, `DEU`, `FRA`, `GBR`, `USA`, `WLD`)
  - `Indicator_Name`: Life expectancy at birth, total (years)
  - `Year`: Annual historical surveillance time series
  - `Life_Expectancy`: Metric estimate benchmarked against the Netherlands

---

## 4. Scientific Dataset Sets (Bundles)

Datasets can be queried and cached individually or in domain-specific bundles:

| Set Identifier | Title | Member Datasets |
| :--- | :--- | :--- |
| `epidemiology` | Epidemiology & Public Health Cohorts | `ecdc-covid-vaccine`, `dutch-dalys-pmc`, `cbs-vtv-phfs`, `cbs-vtv-determinants`, `cbs-population-forecast`, `who-gho-odata`, `health-ri-catalogue` |
| `environmental_ecology` | Environmental & Ecological Systems | `foto-nl-water-pollution`, `unep-gems-water`, `icp-im-air-pollution`, `loobos-flux-meteorology`, `sa-fari-wildlife` |
| `neuro_behavioral` | Neurobehavioral & Cognitive Studies | `mendeley-neurodiversity`, `edinburgh-share-mh`, `liss-panel-nl`, `openneuroscience-ntr` |
| `all` | Unified Research Repository | All 16 scientific and clinical datasets |

---

## 5. High-Speed Parquet Caching & Dual-Store Architecture

To achieve sub-second query latency and bypass remote network bottlenecks, every dataset is stored in a dual-layer local cache:

```text
data_cache/
├── cache_manifest.json          # Global manifest indexing all cached cohorts
└── <dataset_id>/
    ├── metadata.json            # Snapshot: MD5 hash, row counts, byte sizes, TTL
    ├── data.csv                 # Raw pristine download (audit trail)
    ├── data.parquet             # High-speed columnar Snappy-compressed store
    └── unzipped/                # Extracted member tables (for .zip packages)
        ├── member_table_1.csv
        └── member_table_2.csv
```

### 5.1 Parquet Performance Characteristics
- **Read Throughput**: 813,367 rows of ECDC COVID-19 data load in **< 150 milliseconds**.
- **Compression Ratio**: 93.4% reduction versus uncompressed CSV (e.g. 52.6 MB CSV compiles to 3.5 MB Parquet).
- **Engine**: Apache Arrow (`pyarrow`) with Snappy block compression.

---

## 6. Multi-Table Zip Archive Packages

When datasets contain bundled multi-table archives (such as UNEP GEMS/Water, SA-FARI Wildlife AI, or FOTO-NL):
1. The cache manager automatically unpacks the archive into `data_cache/<dataset_id>/unzipped/`.
2. Inspects and catalogs all member data tables (`.csv`, `.tsv`, `.parquet`).
3. The interactive web explorer provides a **Zip Archive Package Banner** dropdown to switch between tables seamlessly.
4. Each member table updates variable citations, record counts, and pagination independently.

---

## 7. REST API Access Reference

The platform provides a comprehensive REST API to interact with datasets, caches, and exploratory views:

### 7.1 List All Datasets
- **Endpoint**: `GET /api/datasets`
- **Response**: Array of dataset objects enriched with real-time cache status, file sizes, and record counts.

### 7.2 Interactive Exploration & Codebook
- **Endpoint**: `GET /api/datasets/<dataset_id>/preview`
- **Query Parameters**:
  - `limit` (default: 100): Number of rows to return.
  - `offset` (default: 0): Starting row offset.
  - `q`: Case-insensitive substring search filter across all columns.
  - `sort_by`: Column name to sort on.
  - `sort_order` (`asc` or `desc`): Sort order.
  - `member`: Target table name inside a zip archive package.
- **Response Payload**:
  ```json
  {
    "dataset_id": "dutch-dalys-pmc",
    "total_rows": 2000,
    "filtered_rows": 2000,
    "columns": ["kenteken", "voertuigsoort", "merk", "..."],
    "records": [...],
    "variables": [
      {
        "index": 1,
        "raw_name": "kenteken",
        "formatted_name": "Vehicle Registration License Plate Identifier",
        "dtype": "Character"
      }
    ],
    "variables_citation_text": "Variables Cited (N=102): [1] kenteken (Vehicle Registration License Plate Identifier) ...",
    "package_members": []
  }
  ```

### 7.3 Cache Manifest & Set Diagnostics
- **Endpoint**: `GET /api/cache` — Storage summary, disk usage, and set completion status.
- **Endpoint**: `GET /api/cache/sets` — Definitions and dataset members of all scientific sets.

### 7.4 Batch Refresh & Clearing
- **Endpoint**: `POST /api/cache/refresh`
  - Body: `{ "set_id": "epidemiology" }` or `{ "dataset_id": "dutch-dalys-pmc" }`
- **Endpoint**: `POST /api/cache/clear`
  - Body: `{}` (clears entire cache) or `{ "dataset_id": "..." }`
