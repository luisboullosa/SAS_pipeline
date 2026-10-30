# COVID-19 Vaccine Tracker & Clinical Programming Platform
## Engineering Specifications (SPECS-2026.09)

---

### 1. System Architecture & Remote SAS Connectivity

#### 1.1 Overview
The platform provides an enterprise clinical programming and epidemiological reporting suite interfacing directly with **SAS OnDemand for Academics (ODA)** via `saspy` and local analytical engines (R and Python/Pandas).

```
+-------------------------------------------------------------------------+
|                              Web Tier                                   |
|   Flask Application (app.py) & Responsive UI (index.html, Bootstrap 5)  |
+------------------------------------+------------------------------------+
                                     |
                REST API Requests & Thread Synchronization
                               (sas_lock)
                                     |
                                     v
+------------------------------------+------------------------------------+
|                         Session Manager                                 |
|            ensure_sas_ready(): Auto-Reconnect & Keepalive               |
+------------------------------------+------------------------------------+
                                     |
                         IOM Bridge (Java 8 JRE)
                 Proprietary SAS Encryption Ciphers
                                     |
                                     v
+------------------------------------+------------------------------------+
|                       SAS ODA Cloud (EU West)                           |
|             odaws01-euw1.oda.sas.com / odaws02-euw1.oda.sas.com          |
|   WORK Library (COVID_VACCINE: 813,367 rows, PROC SQL, SGPLOT, ODS PDF) |
+-------------------------------------------------------------------------+
```

#### 1.2 Remote Environment Configuration
- **Runtime JRE**: Java 8 OpenJDK (configured via `JAVA_HOME` or `python/sascfg_personal.py`). Required for legacy SAS IOM encryption key exchange.
- **IOM Encryption Libraries**: SAS IOM JARs (`sas.rutil.jar`, `sas.rutil.nls.jar`, `sastpj.rutil.jar`) loaded into `saspy/java/iomclient/`.
- **Credential Storage**: Strict OS-level storage via `_authinfo` file in user profile root (`~/_authinfo` or `%USERPROFILE%\_authinfo`) with secure trailing newline. No credentials passed in CLI or source code.
- **ODA Server Region**: European home region (`odaws01-euw1.oda.sas.com`, `odaws02-euw1.oda.sas.com`).
- **Session Auto-Recovery**: Detects idle session timeouts (>15 minutes inactivity) and transparently reinitializes the connection and reloads datasets without HTTP 500 crashes.

---

### 2. Clinical Data Standards & Pipeline Derivations

#### 2.1 SDTM / ADaM Macros
The platform implements standard CDISC-aligned clinical macros in both R and Python:
- **Date Standardization (`%std_date`)**:
  - Input: Non-standard character date formats (`DD-MON-YYYY`, `MM/DD/YYYY`, `YYYY.MM.DD`).
  - Output: ISO 8601 formatted date string (`YYYY-MM-DD`).
- **Study Day Interval Calculation (`%calc_interval`)**:
  - Formula: $\text{Interval} = \text{EndDate} - \text{StartDate} + 1$ (if $\text{EndDate} \ge \text{StartDate}$, else missing/`None`).
  - CDISC Compliant: Accounts for absence of "Day 0" in study day reckoning.
- **EPOCH Assignment (`%derive_epoch`)**:
  - Inputs: Demographics (`DM`) and Trial Arms (`TA`).
  - Derivation: Structural merge based on `ARMCD` and visit date interval to classify observation into `SCREENING`, `TREATMENT`, or `FOLLOW-UP`.

---

### 3. Dashboard REST API Specifications

#### 3.1 `GET /api/datasets`
- **Description**: Returns all registered datasets in the platform (both active live SAS datasets and curated catalogue research datasets).
- **Response Schema**:
  ```json
  [
    {
      "id": "ecdc-covid-vaccine",
      "name": "ECDC COVID-19 Vaccine Tracker",
      "provider": "European Centre for Disease Prevention and Control (ECDC) / data.europa.eu",
      "category": "Epidemiology & Public Health",
      "records_count": "813,367 rows",
      "status": "active",
      "url": "https://opendata.ecdc.europa.eu/covid19/vaccine_tracker/csv/data.csv",
      "description": "Weekly COVID-19 vaccine uptake...",
      "badge": "Live SAS Engine"
    },
    ...
  ]
  ```

#### 3.2 `GET /api/countries`
- **Description**: Returns all reporting countries present in the dataset.
- **Response Schema**:
  ```json
  [
    { "code": "AT", "name": "Austria" },
    { "code": "FR", "name": "France" },
    ...
  ]
  ```
- **Sorting**: Alphabetical by full English country name (`name`).

#### 3.2 `POST /api/years`
- **Description**: Returns available reporting years for selected countries.
- **Request Body**:
  ```json
  { "countries": ["FR", "DE"] } // or ["ALL"]
  ```
- **Response**: Array of 4-digit string years sorted chronologically, e.g. `["2020", "2021", "2022", "2023"]`.

#### 3.3 `POST /api/age_groups`
- **Description**: Returns available target age groups for the filtered countries and years.
- **Request Body**:
  ```json
  { "countries": ["FR"], "years": ["2021"] }
  ```
- **Response Schema**:
  ```json
  [
    { "code": "ALL", "name": "All Ages / Total Population" },
    { "code": "Age18_24", "name": "18 – 24 years old" },
    ...
  ]
  ```
- **Label Requirement**: All age brackets must include the explicit wording **"years old"** (e.g. `18 – 24 years old`, `80+ years old`, `Under 18 years old (<18)`).
- **Ordering**: The `"ALL"` group is placed at index 0.

#### 3.4 `GET /api/recent_reports`
- **Description**: Returns metadata for generated PDF reports in descending order of creation time.
- **Response Schema**:
  ```json
  [
    {
      "filename": "report_FR_DE_2021_ALL_AGES.pdf",
      "title": "Report: FR_DE | 2021 | ALL_AGES",
      "url": "/static/reports/report_FR_DE_2021_ALL_AGES.pdf",
      "timestamp": 1756904123.45,
      "date_formatted": "2026-09-03 14:55:23",
      "size_kb": 87.2
    }
  ]
  ```

#### 3.5 `POST /api/report`
- **Description**: Triggers dynamic SAS SQL aggregation, ODS PDF compilation, and downloads the PDF to local storage.
- **Request Body**:
  ```json
  {
    "countries": ["FR", "DE"], // or ["ALL"]
    "years": ["2021", "2022"], // or ["ALL"]
    "ages": ["ALL"] // or ["Age18_24", "Age25_49"]
  }
  ```
- **Response**:
  ```json
  { "report_url": "/static/reports/report_FR_DE_2021_2022_ALL_AGES.pdf" }
  ```

---

### 4. PDF Report & Visualization Specifications

#### 4.1 Figure & Table Linkage Schema
Each graphical figure in the report is assigned a distinct `Figure ID` cross-referenced with a corresponding `Table ID` located in the tabular section beneath the Executive Summary Table:

| Figure ID | Description | Linked Table ID | Tabular Contents |
|-----------|-------------|-----------------|------------------|
| **Figure 1** | Weekly Vaccine Doses Scatterplot (First: Gray, Second: Black) | **Table 1** | Tabular source data for Figure 1: Week, First Doses (Gray), Second Doses (Black), Total Doses. |
| **Figure 2** | Weekly Vaccine Doses by Age Group (All Ages Total + Cohorts) | **Table 2** | Tabular source data for Figure 2: Week, Age Target Group, Total Doses Administered. |
| **Figure 3** *(Conditional)* | Weekly Vaccine Doses by Country (All Selected Countries + Individual) | **Table 3** | Tabular source data for Figure 3: Week, Reporting Country, Total Doses Administered. |

#### 4.2 Document Page Ordering
1. **Visualizations Section**:
   - **Figure 1**: Weekly Dose Scatterplot (`valuesrotate=diagonal`, First Dose: Gray, Second Dose: Black).
   - **Figure 2**: Age Group Breakdown Line Chart (All Ages Total reference line + individual age bracket lines).
   - **Figure 3** *(if >1 country selected)*: Country Comparative Line Chart (All Selected Countries reference line + individual country lines).
2. **Tabular Audit Section**:
   - **Executive Summary Table**: Aggregated overview of weekly total intake.
   - **Table 1 (Linked to Figure 1)**: First vs. Second Dose Administrations.
   - **Table 2 (Linked to Figure 2)**: Weekly Administrations by Age Target Group.
   - **Table 3 (Linked to Figure 3)** *(if applicable)*: Weekly Administrations by Reporting Country.

#### 4.3 Publication-Ready Graph Templates (Nature & Ecology Journal Standards)
- **Style Definitions**:
  - `styles.NatureJournal`:
    - Clean sans-serif typography (`Arial, Helvetica, sans-serif`) with strict font hierarchy: 10.5pt bold titles, 9pt bold axis labels, 8pt tick values, 7.5pt footnotes.
    - Minimalist L-shaped axes (`frameborder=off`, background `#FFFFFF`, clean thin axes `#1A1A1A`).
    - Standard Nature palette: `#1A1A1A` (near black), `#737373` (slate gray), `#E64B35` (Nature coral red), `#00A087` (Nature teal), `#3C5488` (Nature navy), `#F39B7F` (soft salmon), `#8491B4` (slate indigo), `#91D1C2` (pale sage).
  - `styles.EcologyJournal`:
    - Earth and environmental palette: `#2C5E3B` (deep forest green), `#8C6239` (soil brown), `#2B547E` (catchment blue), `#D4A017` (canopy amber), `#556B2F` (dark olive), `#708090` (mineral slate).
    - Subtle environmental grid lines (`cxe8ede8`).
- **Layout & Sizing Standards**:
  - Publication vector resolution: `dpi=300`.
  - Dimensions: 7.2in × 4.4in, `noborder`.
  - Axis offsets: `offsetmin=0.02 offsetmax=0.02` with diagonal tick labels for time series.
  - Borderless top outside legends: `keylegend / location=outside position=top noborder;`.
- **Reusable SAS Library**: Available in `sas_templates/styles.sas`, `sas_templates/graph_templates.sas`, and `sas_templates/macros.sas`.

---

### 5. UI/UX Specifications

- **Multi-Selection Controls**: Checkboxes with independent scrollable lists.
- **Two-Way All Selection Toggle**:
  - Clicking "All" checks all individual items.
  - Clicking "All" again unchecks all items.
  - Unchecking any single individual item unchecks "All".
  - Checking all individual items automatically re-checks "All".
- **Recent Reports Card**: Displayed on the starting page with direct "View" (renders in iframe) and "Download" buttons.
- **Contextual Dataset Subsetting Navigation Bar (`#stepNavBar`)**:
  - **Landing Page Clarity**: The step navigation bar (`Datasets Hub / Countries / Horizon / Demographics & Style / Report`) is completely hidden on the Datasets landing view (`step 0`) and during dataset exploration (`#exploreView`), keeping the catalogue uncluttered.
  - **Dataset-Activated Subsetting Workflow**: When a dataset is chosen for analysis (e.g. clicking "Analyze Dataset" on ECDC COVID-19 Surveillance), the bar reveals itself directly above the subsetting interface.
  - **Dataset-Specific Variable Mapping**: The bar displays an active dataset identifier badge and the respective subsetting variables configured for that dataset (`DATASET_WORKFLOWS`):
    - *ECDC COVID-19 Surveillance*: `1 Countries` (Reporting Country cohort), `2 Horizon` (Surveillance window), `3 Demographics & Style` (Age brackets & Journal theme), `4 Report` (SAS Publication PDF).
    - *UNEP GEMS/Water*: `1 Stations`, `2 Horizon`, `3 Parameters`, `4 Report`.
    - *SA-FARI Wildlife AI*: `1 Species`, `2 Cameras`, `3 Tracklets`, `4 Report`.
  - **Seamless Navigation**: Includes a dedicated `← Datasets Hub` button to return to the catalog at any time, instantly hiding the bar upon return.

---

### 6. Dataset & Sets-of-Datasets Caching Engine

- **Architecture**: Dual-layer persistent cache (`data_cache/`):
  - **Columnar Format**: Apache Parquet (Snappy compression via PyArrow) providing 93%+ compression and sub-second DataFrame loads.
  - **Raw Store**: Preserves original CSV / raw downloads for audit and provenance.
  - **Metadata Snapshot**: `metadata.json` tracking record count, byte sizes, MD5 hash, columns, and TTL (168h default).
  - **Global Manifest**: `data_cache/cache_manifest.json` indexing all stored cohorts.
- **Scientific Dataset Sets (Bundles)**:
  - Detailed catalog, access protocols, and variable codebooks documented in [`docs/DATASETS.md`](DATASETS.md).
  - `epidemiology`: COVID-19 Vaccine Tracker, Dutch DALYs (PMC / RDW), Dutch PHFS VTV Burden of Disease (RIVM / CBS `cbsodata`), Dutch Lifestyle Determinants (CBS `85464NED`), Dutch Population Forecast 2022–2070 (CBS `85323NED`), WHO Global Health Observatory Longevity Benchmarks, Health-RI National Registries.
  - `environmental_ecology`: FOTO-NL Water Chemistry, UNEP GEMS/Water, ICP IM Air Pollution, Loobos Ecosystem Tower, SA-FARI Open Wildlife Video Dataset.
  - `neuro_behavioral`: Mendeley Neurodiversity Profiles, SHARE-MH Cohort, LISS Panel Netherlands, Netherlands Twin Register (NTR).
  - `all`: Unified cache containing all 16 scientific datasets across all disciplines.
- **REST Endpoints**:
  - `GET /api/cache`: Returns total storage usage, record counts, dataset details, and set completion status.
  - `GET /api/cache/sets`: Returns available scientific sets with member dataset IDs.
  - `POST /api/cache/refresh`: Supports `{ "dataset_id": "..." }`, `{ "set_id": "..." }`, or `{ "dataset_ids": [...] }`.
  - `POST /api/cache/clear`: Selectively clears one dataset or clears all cache.

---

### 7. Interactive Dataset Exploration & Filterable Table

- **Explore Endpoint**: `GET /api/datasets/<dataset_id>/preview?limit=100&offset=0&q=...&sort_by=...&sort_order=...&member=...`
  - Returns paginated records, total row counts, filtered row counts, column list, field data types, cache status, variables codebook, and zip package member listings.
  - Auto-caches/indexes remote datasets on demand if not already in cache.
  - Full-text multi-column search filtering.
- **UI Exploration View (`#exploreView`)**:
  - Live metadata bar: total records, fields count with variable range (`Var #1 to #N`), storage format, and local/remote footprint.
  - Real-time search filter across all columns with debounce.
  - Page size selection (50, 100, 250, 500 rows).
  - Column sorting with ascending/descending indicators.
  - Download visible/filtered rows as CSV (`downloadFilteredExploreCSV()`).
  - Seamless navigation back to the Datasets Hub (`← Back to Datasets Hub`).

---

### 8. Zip Archive Package Extraction & Member Datasets Explorer

- **Automatic Archive Unpacking**:
  - Whenever a dataset archive is downloaded or cached as a `.zip` file (e.g. UNEP GEMS/Water `GFQA_v3.zip`, SA-FARI `sa_fari_metadata_package.zip`, or FOTO-NL monitoring packages):
  - The cache manager extracts the zip into `data_cache/<dataset_id>/unzipped/`.
  - Scans and indexes all discrete member data tables (`.csv`, `.tsv`, `.parquet`, `.xlsx`, `.json`).
- **Package Navigator UI (`#explorePackageBanner`)**:
  - Displays the active zip archive status and total member tables count.
  - Provides an interactive dropdown selector to switch between different member tables in the package.
  - Switching immediately updates the preview table, record counts, and variable codebook to reflect the selected member table.

---

### 9. Variable Numbering, Formatted Names & Codebook Citations

- **1-Based Variable Numbering**: Every variable across all datasets is assigned a standardized 1-based variable number (`Var #1`, `Var #2`, ...).
- **Clinical & Scientific Formatted Names**: Raw column keys are mapped to rigorous human-readable formatted names via `VARIABLE_FORMAT_MAP` with intelligent snake_case/camelCase heuristics and scientific acronym preservation.
- **Dual Table Header Presentation**:
  - Table headers display the variable number badge (`Var #N`), the raw variable key, and the formatted human-readable name below it.
- **Codebook Specification & Citation Panel**:
  - Displays all cited variables with formatted pills showing index, raw name, formatted title, and data type (`Integer`, `Decimal`, `Datetime`, `Character`).
  - **Copy Codebook Citation**: One-click clipboard export of standard academic/clinical citation strings (e.g. `Variables Cited (N=18): [1] YearWeekISO (Calendar Year & Week [ISO 8601]) • [2] ReportingCountry ...`).

---

### 10. Socrata Open Data API (SODA 3 Views Query API) & Dutch Environmental Mobility Integration

- **Modern SODA 3 Views Query API Endpoint**:
  - Resource URI: `https://opendata.rdw.nl/api/v3/views/2snn-6yr9/query.csv` (Open Data RDW: Gekentekende voertuigen / Environmental Mobility & Population Exposure Cohort).
  - Specifications: Built against Socrata developer standards ([https://dev.socrata.com/](https://dev.socrata.com/)).
  - Backward Compatibility: Full fallback support for legacy SODA 2.x endpoints (`/resource/2snn-6yr9.csv`).
- **Secure Secret Ingestion (`python/dashboard/socrata_client.py`)**:
  - Path: `D:\Development\SAS\.secrets\.auth.txt` (protected by `.gitignore`, never printed or echoed in logs/transcripts).
  - Keys: `API_KEY_ID` and `RDW_API_KEY_SECRET`.
  - Authentication: Socrata HTTP Basic Authentication (`Authorization: Basic <base64(API_KEY_ID:RDW_API_KEY_SECRET)>`).
- **SODA 3 SoQL SQL Querying Engine**:
  - Native SoQL query string formatting via `query` parameter: `SELECT * [WHERE ...] [ORDER BY ...] LIMIT ... OFFSET ...`.
  - Streamed live into `data_cache/dutch-dalys-pmc/data.csv` and compiled into columnar Snappy-compressed Parquet (`data.parquet`).
  - Formatted variables mapping 102 Dutch vehicle characteristics, mass dynamics, emissions classifications, and SODA 3 metadata into human-readable scientific titles.
