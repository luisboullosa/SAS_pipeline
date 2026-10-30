import os
import urllib.request
import json
import threading
import pandas as pd
from flask import Flask, render_template, request, jsonify, url_for
import saspy

app = Flask(__name__)
DATA_PATH = os.path.join(os.path.dirname(__file__), 'data.csv')
REPORTS_DIR = os.path.join(os.path.dirname(__file__), 'static', 'reports')

sas_lock = threading.Lock()

try:
    from cache_manager import DatasetCacheManager, DATASET_SETS
except ImportError:
    from python.dashboard.cache_manager import DatasetCacheManager, DATASET_SETS

cache_mgr = DatasetCacheManager()

# Ensure local cache for primary active dataset
if not cache_mgr.is_cached('ecdc-covid-vaccine'):
    print("Initializing local Parquet dataset cache for ECDC COVID-19 Vaccine Tracker...")
    if not os.path.exists(DATA_PATH):
        api_url = "https://data.europa.eu/api/hub/search/datasets/covid-19-vaccine-tracker"
        csv_url = None
        try:
            print("Fetching metadata from European Data API...")
            req = urllib.request.urlopen(api_url)
            metadata = json.loads(req.read())
            for dist in metadata.get('result', {}).get('distributions', []):
                if dist.get('format', {}).get('id') == 'CSV':
                    for u in dist.get('download_url', []):
                        if 'vaccine' in u.lower():
                            csv_url = u
                            break
                if csv_url: break
        except Exception as e:
            print(f"API metadata lookup note: {e}")
        
        if not csv_url:
            csv_url = "https://opendata.ecdc.europa.eu/covid19/vaccine_tracker/csv/data.csv"
        
        try:
            print(f"Downloading dataset from: {csv_url}")
            urllib.request.urlretrieve(csv_url, DATA_PATH)
            print("Dataset downloaded successfully.")
        except Exception as e:
            print(f"Download warning: {e}")

    try:
        cache_mgr.cache_dataset('ecdc-covid-vaccine', source_path_or_url=DATA_PATH)
    except Exception as e:
        print(f"Cache initialization error: {e}")

sas = None
SAS_READY = False

VTV_PARQUET = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..', '..', 'projects', 'dutch_phfs_burden_of_disease', 'data', 'dutch_dalys_estimates.parquet')
)
VTV_CSV = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..', '..', 'projects', 'dutch_phfs_burden_of_disease', 'data', 'dutch_dalys_estimates.csv')
)

def ensure_vtv_sas_tables():
    global sas
    if sas is None:
        return False
    try:
        if not sas.exist('vtv_dalys', 'work'):
            print("Uploading VTV DALYs dataset to SAS WORK...")
            sas.submit("%let workpath = %sysfunc(pathname(work));")
            workpath = sas.symget('workpath')
            if workpath:
                workpath = workpath.strip()
                if os.path.exists(VTV_CSV):
                    sas.upload(VTV_CSV, f"{workpath}/dutch_dalys.csv")
                    sas.submit(f"""
                    proc import datafile="{workpath}/dutch_dalys.csv" out=work.vtv_dalys dbms=csv replace;
                        guessingrows=2000;
                    run;
                    """)
                    print("work.vtv_dalys loaded successfully into SAS.")
            
            trend_data_file = os.path.abspath(
                os.path.join(os.path.dirname(__file__), '..', '..', 'projects', 'dutch_phfs_burden_of_disease', 'sas', 'vtv_trendscenario_data.sas')
            )
            if os.path.exists(trend_data_file):
                with open(trend_data_file, 'r', encoding='utf-8') as f:
                    trend_code = f.read()
                sas.submit(trend_code)
                print("work.vtv_trendscenario canonical tables loaded successfully into SAS.")
        return sas.exist('vtv_dalys', 'work')
    except Exception as e:
        print(f"Notice loading VTV tables into SAS: {e}")
        return False

def ensure_sas_ready():
    global sas, SAS_READY
    if os.environ.get('TESTING') == '1' or os.environ.get('SKIP_SAS_INIT') == '1':
        return False
    with sas_lock:
        try:
            if sas is not None and sas.exist('countries', 'work'):
                ensure_vtv_sas_tables()
                return True
        except Exception:
            pass
        
        print("Ensuring active SAS session (connecting/reloading)...")
        try:
            cfg_path = os.path.join(os.path.dirname(__file__), '..', 'sascfg_personal.py')
            sas = saspy.SASsession(cfgfile=cfg_path, cfgname='oda')
            sas_load_code = """
            filename ecdc url "https://opendata.ecdc.europa.eu/covid19/vaccine_tracker/csv/data.csv";
            proc import datafile=ecdc out=work.covid_vaccine dbms=csv replace;
                guessingrows=1000;
            run;
            proc sql;
                create table work.countries as
                select distinct ReportingCountry
                from work.covid_vaccine
                order by ReportingCountry;
            quit;
            """
            sas.submit(sas_load_code)
            ensure_vtv_sas_tables()
            SAS_READY = True
            print("SAS session ready and dataset loaded successfully.")
            return True
        except Exception as e:
            print(f"SAS connection failed: {e}")
            SAS_READY = False
            return False

from datetime import datetime

# Initialize at startup
ensure_sas_ready()
try:
    df_cached = cache_mgr.load_dataframe('ecdc-covid-vaccine')
    if df_cached is not None:
        cols = [c for c in ['YearWeekISO', 'ReportingCountry', 'TargetGroup', 'FirstDose', 'SecondDose', 'DoseAdditional1'] if c in df_cached.columns]
        df_sub = df_cached[cols].dropna()
        print(f"Loaded {len(df_sub)} rows instantaneously from high-speed Parquet cache.")
    elif os.path.exists(DATA_PATH):
        df_sub = pd.read_csv(DATA_PATH, usecols=['YearWeekISO', 'ReportingCountry', 'TargetGroup', 'FirstDose', 'SecondDose', 'DoseAdditional1'], low_memory=False).dropna()
    else:
        df_sub = None
except Exception:
    df_sub = None

df_vtv = None
try:
    if os.path.exists(VTV_PARQUET):
        df_vtv = pd.read_parquet(VTV_PARQUET)
    elif os.path.exists(VTV_CSV):
        df_vtv = pd.read_csv(VTV_CSV)
    if df_vtv is not None:
        print(f"Loaded {len(df_vtv)} rows into df_vtv from Dutch PHFS DALYs estimates.")
except Exception as e:
    print(f"Notice loading VTV dataset: {e}")

VTV_DISEASE_MAP = {
    'ALL': 'All Disease Groups & Conditions (Total Combined + Breakdown)',
    'Respiratory & Pulmonary Diseases': 'Respiratory & Pulmonary Diseases (COPD & Asthma)',
    'Musculoskeletal & Joint Diseases': 'Musculoskeletal & Joint Diseases (Artrose, Back/Neck)',
    'Accidental Injuries & Poisonings': 'Accidental Injuries & Poisonings (Falls, Trauma)',
    'All Cancers & Neoplasms': 'All Cancers & Neoplasms (Oncology Aggregate)',
    'Breast Cancer': 'Breast Cancer (Mamma Carcinoma)',
    'Prostate Cancer': 'Prostate Cancer (Prostate Carcinoma)',
    'Colorectal Cancer': 'Colorectal Cancer (Colon & Rectum)',
    'Trachea, Bronchus & Lung Cancer': 'Trachea, Bronchus & Lung Cancer',
    'COVID-19 Inpatient Morbidity': 'COVID-19 Inpatient Morbidity',
    'Diabetes Mellitus': 'Diabetes Mellitus (Type 1 & 2)',
    'Mental & Behavioral Disorders': 'Mental & Behavioral Disorders (Dementia & Psychiatric)',
    'Major Depressive Disorders': 'Major Depressive Disorders (Depression)',
    'Cardiovascular & Circulatory Diseases': 'Cardiovascular & Circulatory Diseases (CVD Total)',
    'Coronary Artery Disease (IHD)': 'Coronary Artery Disease (Ischemic Heart Disease)',
    'Heart Failure': 'Heart Failure (Decompensated Heart Failure)',
    'All Causes (Total)': 'All Causes (Total Inpatient Morbidity & Mortality)'
}

VTV_METRIC_MAP = {
    'DALY': 'Disability-Adjusted Life Years (DALY = YLL + YLD)',
    'YLL': 'Years of Life Lost (Premature Mortality - YLL)',
    'YLD': 'Years Lived with Disability (Non-fatal Morbidity - YLD)',
    'Inpatient_Rate_Per10k': 'Inpatient Admission Rate (per 10,000)',
    'Inpatient_Admissions': 'Total Hospital Inpatient Admissions'
}

def get_recent_reports_list():
    if not os.path.exists(REPORTS_DIR):
        return []
    
    files = [f for f in os.listdir(REPORTS_DIR) if f.lower().endswith('.pdf')]
    reports = []
    for fname in files:
        fpath = os.path.join(REPORTS_DIR, fname)
        try:
            mtime = os.path.getmtime(fpath)
            size_kb = round(os.path.getsize(fpath) / 1024, 1)
            name_parts = fname.replace('.pdf', '').split('_')
            display_name = fname
            if fname == 'VTV_2024_Trendscenario_Nature_Report.pdf':
                display_name = "RIVM VTV-2024 Trendscenario: Nature Replication Report (1990–2050)"
            elif fname.startswith('report_vtv_'):
                parts = fname.replace('.pdf', '').split('_')
                d_part = parts[2] if len(parts) > 2 else "All Conditions"
                y_part = parts[3] if len(parts) > 3 else "All Years"
                m_part = parts[5] if len(parts) > 5 else "DALY"
                display_name = f"VTV DALY Report: {d_part} | {y_part} | {m_part}"
            elif len(name_parts) >= 4:
                c_part = name_parts[1]
                y_part = name_parts[2]
                a_part = "_".join(name_parts[3:])
                display_name = f"COVID Report: {c_part} | {y_part} | {a_part}"
            
            created_str = datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M:%S')
            reports.append({
                'filename': fname,
                'title': display_name,
                'url': f"/static/reports/{fname}",
                'timestamp': mtime,
                'date_formatted': created_str,
                'size_kb': size_kb
            })
        except Exception:
            pass
            
    reports.sort(key=lambda x: x['timestamp'], reverse=True)
    return reports

DATASETS = [
    {
        'id': 'ecdc-covid-vaccine',
        'name': 'ECDC COVID-19 Vaccine Tracker',
        'provider': 'European Centre for Disease Prevention and Control (ECDC) / data.europa.eu',
        'category': 'Epidemiology & Public Health',
        'records_count': '813,367 rows',
        'status': 'active',
        'url': 'https://opendata.ecdc.europa.eu/covid19/vaccine_tracker/csv/data.csv',
        'description': 'Weekly COVID-19 vaccine uptake by target age groups, doses (1st, 2nd, additional), and European reporting countries. Fully integrated with live SAS Cloud SQL aggregation and ODS PDF reporting.',
        'badge': 'Live SAS Engine'
    },
    {
        'id': 'foto-nl-water-pollution',
        'name': 'FOTO-NL Chemical Pollution Monitoring in Dutch Surface Waters',
        'provider': 'RIVM & Dutch Regional Water Boards / Zenodo',
        'category': 'Environmental Chemistry & Toxicology',
        'records_count': '35,756,662 clean records (51.5M raw)',
        'status': 'catalogue',
        'url': 'https://zenodo.org/records/19494234',
        'description': 'Harmonized longitudinal chemical pollution data across 21 Dutch regional water boards and Rijkswaterstaat for the Rhine and Meuse (1954–2020) with verified CAS-numbers and pretreatment flags.',
        'badge': '35M+ Records'
    },
    {
        'id': 'unep-gems-water',
        'name': 'UNEP GEMS/Water Global Freshwater Quality Archive',
        'provider': 'United Nations Environment Programme (UNEP) / ICWRGC & BfG / Zenodo',
        'category': 'Global Hydrology & Water Quality',
        'records_count': '50,000,000+ measurements (22,982 stations)',
        'status': 'catalogue',
        'url': 'https://zenodo.org/records/18459694',
        'description': 'Global freshwater quality archive covering 622 water quality parameters across 42 UN member states from 1906 to 2024, compiled by the GEMS/Water Data Centre.',
        'badge': '50M+ Measurements'
    },
    {
        'id': 'dutch-dalys-pmc',
        'name': 'Dutch Burden of Disease & Environmental Mobility Study (RDW / RIVM)',
        'provider': 'RDW Open Data (Socrata SODA 3) & RIVM / PMC',
        'category': 'Public Health & Environmental Epidemiology',
        'records_count': 'Live SODA 3 Stream • 102 Variables',
        'status': 'catalogue',
        'url': 'https://opendata.rdw.nl/api/v3/views/2snn-6yr9/query.csv',
        'socrata_endpoint': 'https://opendata.rdw.nl/api/v3/views/2snn-6yr9/query.csv',
        'description': 'Dutch national burden of disease & environmental mobility study accessible live via Socrata SODA 3 Views Query API (https://opendata.rdw.nl/api/v3/views/2snn-6yr9/query.csv) with Socrata API credentials (API_KEY_ID & RDW_API_KEY_SECRET) measuring vehicle emissions, mass dynamics, and environmental health indicators.',
        'badge': 'SODA 3 Query API'
    },
    {
        'id': 'cbs-vtv-phfs',
        'name': 'Dutch Public Health Foresight Study: DALYs & Disease Burden (RIVM / CBS)',
        'provider': 'RIVM & Statistics Netherlands (CBS Open Data / cbsodata)',
        'category': 'Public Health & Burden of Disease Epidemiology',
        'records_count': '1,536 Stratified DALY Estimates (16 Conditions)',
        'status': 'catalogue',
        'url': 'https://academic.oup.com/eurpub/article/35/Supplement_4/ckaf161.580/8303243',
        'cbs_table': '84067NED',
        'description': 'Comprehensive Dutch burden of disease estimates measuring Disability-Adjusted Life Years (DALYs), YLL, and YLD across VTV disease categories, age strata, and sex based on Hilderink et al. (Eur J Public Health 2025) and CBS Open Data (84067NED & 7052_95).',
        'badge': 'cbsodata Engine'
    },
    {
        'id': 'cbs-vtv-determinants',
        'name': 'Dutch Lifestyle & Health Determinants Monitor (CBS / RIVM)',
        'provider': 'RIVM & Statistics Netherlands (CBS Open Data / cbsodata)',
        'category': 'Public Health & Behavioral Epidemiology',
        'records_count': '720 Stratified Multi-Year Cohorts',
        'status': 'catalogue',
        'url': 'https://opendata.cbs.nl/#/CBS/nl/dataset/85464NED/table',
        'cbs_table': '85464NED',
        'description': 'Empirical lifestyle determinants from the Dutch Health Survey & Lifestyle Monitor measuring smoking prevalence, alcohol consumption, physical inactivity, and BMI/overweight across demographic strata and education levels.',
        'badge': 'cbsodata Engine'
    },
    {
        'id': 'cbs-population-forecast',
        'name': 'Dutch Population Forecast 2022–2070 (CBS Bevolkingsprognose)',
        'provider': 'Statistics Netherlands (CBS Open Data / cbsodata)',
        'category': 'Demography & Actuarial Epidemiology',
        'records_count': '240 Forecast Intervals (2022–2070)',
        'status': 'catalogue',
        'url': 'https://opendata.cbs.nl/#/CBS/nl/dataset/85323NED/table',
        'cbs_table': '85323NED',
        'description': 'Official CBS national population projections across age categories (0-20, 20-65, 65+), demographic pressure metrics (groene druk, grijze druk), and 67%/95% prognosis confidence intervals underlying VTV-2024.',
        'badge': 'cbsodata Engine'
    },
    {
        'id': 'who-gho-odata',
        'name': 'WHO Global Health Observatory: Longitudinal Life Expectancy Benchmarks',
        'provider': 'World Health Organization (WHO) & World Bank Open Data',
        'category': 'Global Health Statistics & Longevity',
        'records_count': '396 Multi-Country Benchmark Years (1960–2024)',
        'status': 'catalogue',
        'url': 'https://ghoapi.azureedge.net/api/WHOSIS_000001',
        'description': 'Longitudinal international life expectancy at birth indicators benchmarked across the Netherlands, Germany, France, United Kingdom, United States, and Global World aggregates.',
        'badge': 'WHO / World Bank API'
    },
    {
        'id': 'health-ri-catalogue',
        'name': 'National Health Data Catalogue (Health-RI Netherlands)',
        'provider': 'Health-RI Netherlands',
        'category': 'Health Research & Life Sciences Infrastructure',
        'records_count': 'National Multi-Registry Index',
        'status': 'catalogue',
        'url': 'https://www.healthdata.nl/en/data-catalogue/about-catalogue',
        'description': 'The Dutch National Health Data Catalogue providing an overview of available health research data, life sciences registries, and clinical biobanks in the Netherlands for secondary use.',
        'badge': 'National Catalogue'
    },
    {
        'id': 'icp-im-air-pollution',
        'name': 'ICP IM: Air Pollution Effects on Ecosystems (1990–Present)',
        'provider': 'Swedish Research Council / researchdata.se',
        'category': 'Atmospheric Pollution & Ecology',
        'records_count': 'Catchment-Scale Longitudinal Data',
        'status': 'catalogue',
        'url': 'https://researchdata.se/en/catalogue/dataset/2024-180',
        'description': 'Long-term monitoring of air pollution impacts on undisturbed small catchment ecosystems across Europe under the UNECE Convention on Long-range Transboundary Air Pollution.',
        'badge': 'Catchment Ecology'
    },
    {
        'id': 'loobos-flux-meteorology',
        'name': 'Loobos Ecosystem Tower Dataset: Fluxes & Meteorology (1996–2021)',
        'provider': 'Earth System Science Data (Copernicus ESSD)',
        'category': 'Micrometeorology & Carbon Cycle',
        'records_count': '25-Year High-Frequency Tower Records',
        'status': 'catalogue',
        'url': 'https://essd.copernicus.org/articles/18/2023/2026/',
        'description': 'Quarter-century continuous eddy-covariance measurements of turbulent fluxes, net ecosystem exchange (NEE), energy balance, and meteorology over a temperate pine forest in the Netherlands.',
        'badge': 'Copernicus ESSD'
    },
    {
        'id': 'mendeley-neurodiversity',
        'name': 'Neurodiversity in Educational Settings: Cognitive & Behavioral Profiles (Ages 10–18)',
        'provider': 'Mendeley Data / Dar Deen, Deen MOHD',
        'category': 'Educational Psychology & Cognitive Neurodiversity',
        'records_count': '420 Students, 12 Trait Domains',
        'status': 'catalogue',
        'url': 'https://data.mendeley.com/datasets/22mw357f2y/1',
        'description': 'Anonymized trait-level observational dataset capturing 12 neurodivergent cognitive and behavioral dimensions (sensory, attention, executive functioning, routine adherence) for youth aged 10–18.',
        'badge': 'Mendeley Data'
    },
    {
        'id': 'edinburgh-share-mh',
        'name': 'SHARE-MH Cohort: Scottish Mental Health Survey',
        'provider': 'University of Edinburgh / Centre for Clinical Brain Sciences',
        'category': 'Clinical Psychiatry & Mental Health Cohort',
        'records_count': 'NHS Linkable Research Cohort',
        'status': 'catalogue',
        'url': 'https://datashare.ed.ac.uk/items/a4b6ea33-6234-424e-988d-ee3329903a1a',
        'description': 'Research-grade individual-level psychiatric survey data linkable to NHS electronic health records and genetic repositories from the Scottish Health Research Register (SHARE).',
        'badge': 'Edinburgh DataShare'
    },
    {
        'id': 'liss-panel-nl',
        'name': 'LISS Panel: Longitudinal Internet Studies for the Social Sciences',
        'provider': 'Centerdata & Tilburg University (Netherlands)',
        'category': 'Longitudinal Social & Population Health',
        'records_count': '5,000 Households / 7,500 Individuals Multi-Wave',
        'status': 'catalogue',
        'url': 'https://www.lissdata.nl/',
        'description': 'Representative Dutch national probability-based longitudinal online survey infrastructure tracking monthly multi-wave studies on health, demographics, cognition, and socio-economic behaviors.',
        'badge': 'Dutch National Panel'
    },
    {
        'id': 'openneuroscience-ntr',
        'name': 'Netherlands Twin Register (NTR)',
        'provider': 'Vrije Universiteit Amsterdam & Open Neuroscience',
        'category': 'Behavioral Genetics & Neuroepidemiology',
        'records_count': '120,000+ Twins & Family Members',
        'status': 'catalogue',
        'url': 'https://openneuroscience.org/Actors/NTR',
        'description': 'Global landmark longitudinal twin-family cohort tracking over 120,000 twins across health, behavior, cognition, and biobanking to disentangle genetic and environmental epidemiology.',
        'badge': 'Twin Family Cohort'
    },
    {
        'id': 'sa-fari-wildlife',
        'name': 'SA-FARI: Open Wildlife Video & Segmentation Dataset',
        'provider': 'Conservation X Labs & Meta / SAM3',
        'category': 'Biodiversity & Wildlife Vision AI',
        'records_count': '11,000+ Videos • 99 Species',
        'status': 'catalogue',
        'url': 'http://conservationxlabs.com/sa-fari',
        'description': 'Open-access wildlife camera trap video dataset with dense spatiotemporal segmentation masks, bounding boxes, and tracklets across 99 species, built with Meta SAM3.',
        'badge': 'Wildlife Vision AI'
    }
]

@app.route('/api/datasets', methods=['GET'])
def get_datasets():
    enriched = []
    manifest = cache_mgr._read_manifest().get('datasets', {})
    for d in DATASETS:
        d_copy = dict(d)
        c_info = manifest.get(d['id'])
        d_copy['is_cached'] = c_info is not None
        d_copy['cache_info'] = c_info
        enriched.append(d_copy)
    return jsonify(enriched)

@app.route('/api/datasets/<dataset_id>/preview', methods=['GET'])
def preview_dataset(dataset_id):
    meta = next((d for d in DATASETS if d['id'] == dataset_id), None)
    if not meta:
        return jsonify({'error': f'Dataset {dataset_id} not found in catalogue'}), 404

    if not cache_mgr.is_cached(dataset_id):
        try:
            cache_mgr.cache_dataset(dataset_id, dataset_meta=meta)
        except Exception as e:
            print(f"Error auto-caching {dataset_id}: {e}")

    # Inspect zip package members and member selection
    member = request.args.get('member') or request.args.get('file')
    package_members = cache_mgr.get_package_members(dataset_id)
    df = None
    if package_members:
        if member:
            df = cache_mgr.load_member_dataframe(dataset_id, member)
        if df is None:
            member = package_members[0]['file_name']
            df = cache_mgr.load_member_dataframe(dataset_id, member)

    if df is None:
        df = cache_mgr.load_dataframe(dataset_id)
        if df is None:
            if dataset_id == 'ecdc-covid-vaccine' and os.path.exists(DATA_PATH):
                df = pd.read_csv(DATA_PATH, low_memory=False)
            else:
                return jsonify({'error': 'Dataset could not be loaded into DataFrame'}), 404

    query = request.args.get('q', '').strip().lower()
    limit = min(int(request.args.get('limit', 100)), 500)
    offset = max(int(request.args.get('offset', 0)), 0)
    sort_by = request.args.get('sort_by')
    sort_order = request.args.get('sort_order', 'asc')

    filtered_df = df
    if query:
        mask = filtered_df.astype(str).apply(lambda col: col.str.lower().str.contains(query, regex=False, na=False)).any(axis=1)
        filtered_df = filtered_df[mask]

    if sort_by and sort_by in filtered_df.columns:
        ascending = (sort_order.lower() != 'desc')
        try:
            filtered_df = filtered_df.sort_values(by=sort_by, ascending=ascending)
        except Exception:
            pass

    total_filtered = len(filtered_df)
    sample = filtered_df.iloc[offset:offset + limit]

    rows = sample.where(pd.notnull(sample), None).to_dict(orient='records')
    columns = list(df.columns)
    dtypes = {col: str(dtype) for col, dtype in df.dtypes.items()}
    cache_info = cache_mgr.get_dataset_info(dataset_id)
    variables = cache_mgr.get_dataset_variables(df)
    variables_citation_text = f"Variables Cited (N={len(variables)}): " + " • ".join(
        f"[{v['number']}] {v['raw_name']} ({v['formatted_name']})" for v in variables
    )

    return jsonify({
        'dataset_id': dataset_id,
        'name': meta.get('name', dataset_id),
        'category': meta.get('category', ''),
        'provider': meta.get('provider', ''),
        'url': meta.get('url', ''),
        'description': meta.get('description', ''),
        'badge': meta.get('badge', ''),
        'total_rows': len(df),
        'total_filtered': total_filtered,
        'limit': limit,
        'offset': offset,
        'columns': columns,
        'dtypes': dtypes,
        'variables': variables,
        'variables_count': len(variables),
        'variables_citation_text': variables_citation_text,
        'is_package': len(package_members) > 0,
        'package_members': package_members,
        'selected_member': member if len(package_members) > 0 else None,
        'cache_info': cache_info,
        'rows': rows
    })

@app.route('/api/cache', methods=['GET'])
def get_cache_status():
    return jsonify(cache_mgr.get_cache_summary())

@app.route('/api/cache/sets', methods=['GET'])
def get_cache_sets():
    return jsonify(DATASET_SETS)

@app.route('/api/cache/refresh', methods=['POST'])
def refresh_cache():
    data = request.get_json() or {}
    set_id = data.get('set_id')
    dataset_id = data.get('dataset_id')
    dataset_ids = data.get('dataset_ids', [])
    force = data.get('force', True)

    if set_id:
        res = cache_mgr.cache_set(set_id, datasets_catalog=DATASETS, force=force)
        return jsonify(res)
    elif dataset_ids:
        results = []
        catalog_map = {d['id']: d for d in DATASETS}
        for did in dataset_ids:
            meta = catalog_map.get(did, {'id': did, 'name': did})
            r = cache_mgr.cache_dataset(did, dataset_meta=meta, force=force)
            results.append(r)
        return jsonify({'status': 'success', 'cached': results})
    elif dataset_id:
        meta = next((d for d in DATASETS if d['id'] == dataset_id), None)
        res = cache_mgr.cache_dataset(dataset_id, dataset_meta=meta, force=force)
        return jsonify(res)
    else:
        # Default: refresh all
        res = cache_mgr.cache_set('all', datasets_catalog=DATASETS, force=force)
        return jsonify(res)

@app.route('/api/cache/clear', methods=['POST'])
def clear_cache():
    data = request.get_json() or {}
    dataset_id = data.get('dataset_id')
    res = cache_mgr.clear_cache(dataset_id=dataset_id)
    return jsonify(res)

@app.route('/api/recent_reports', methods=['GET'])
def get_recent_reports():
    return jsonify(get_recent_reports_list())

@app.route('/')
def index():
    return render_template('index.html', sas_ready=SAS_READY)

COUNTRY_MAP = {
    'AT': 'Austria', 'BE': 'Belgium', 'BG': 'Bulgaria', 'CY': 'Cyprus',
    'CZ': 'Czechia', 'DE': 'Germany', 'DK': 'Denmark', 'EE': 'Estonia',
    'EL': 'Greece', 'ES': 'Spain', 'FI': 'Finland', 'FR': 'France',
    'HR': 'Croatia', 'HU': 'Hungary', 'IE': 'Ireland', 'IS': 'Iceland',
    'IT': 'Italy', 'LI': 'Liechtenstein', 'LT': 'Lithuania', 'LU': 'Luxembourg',
    'LV': 'Latvia', 'MT': 'Malta', 'NL': 'Netherlands', 'NO': 'Norway',
    'PL': 'Poland', 'PT': 'Portugal', 'RO': 'Romania', 'SE': 'Sweden',
    'SI': 'Slovenia', 'SK': 'Slovakia'
}

@app.route('/api/countries', methods=['GET'])
def get_countries():
    if ensure_sas_ready():
        with sas_lock:
            res_df = sas.sd2df("countries", libref="work")
            countries_list = res_df['ReportingCountry'].tolist()
    else:
        countries_list = sorted(df_sub['ReportingCountry'].unique().tolist()) if df_sub is not None else []
    
    result = [{'code': c, 'name': COUNTRY_MAP.get(c, c)} for c in countries_list]
    # Sort alphabetically by full name
    result = sorted(result, key=lambda x: x['name'])
    return jsonify(result)


@app.route('/api/years', methods=['GET', 'POST'])
def get_years():
    if request.method == 'POST':
        data = request.json or {}
        countries = data.get('countries') or data.get('country', [])
    else:
        c_param = request.args.get('countries') or request.args.get('country')
        countries = [x.strip() for x in c_param.split(',')] if c_param else []
    
    if isinstance(countries, str):
        countries = [countries]

    if not countries or 'ALL' in countries or len(countries) >= len(COUNTRY_MAP):
        where_clause = ""
    else:
        quoted = ", ".join(f"'{c}'" for c in countries)
        where_clause = f"where ReportingCountry in ({quoted})"
    
    if ensure_sas_ready():
        code = f"""
        proc sql;
            create table work.years as
            select distinct substr(YearWeekISO, 1, 4) as Year
            from work.covid_vaccine
            {where_clause}
            order by Year;
        quit;
        """
        with sas_lock:
            sas.submit(code)
            res_df = sas.sd2df("years", libref="work")
        years = res_df['Year'].tolist()
    else:
        if df_sub is not None:
            sub = df_sub if not where_clause else df_sub[df_sub['ReportingCountry'].isin(countries)]
            years = sorted(sub['YearWeekISO'].str[:4].unique().tolist())
        else:
            years = []
    return jsonify(years)

AGE_MAP = {
    'ALL': 'All Ages / Total Population',
    'Age0_4': '0 – 4 years old',
    'Age5_9': '5 – 9 years old',
    'Age10_14': '10 – 14 years old',
    'Age15_17': '15 – 17 years old',
    'Age<18': 'Under 18 years old (<18)',
    'Age18_24': '18 – 24 years old',
    'Age25_49': '25 – 49 years old',
    'Age50_59': '50 – 59 years old',
    'Age60_69': '60 – 69 years old',
    'Age70_79': '70 – 79 years old',
    'Age80+': '80+ years old',
    '1_Age<60': 'Under 60 years old (<60)',
    '1_Age60+': '60+ years old',
    'AgeUNK': 'Unknown Age',
    'HCW': 'Healthcare Workers (HCW)',
    'LTCF': 'Long-Term Care Facility Residents (LTCF)'
}

@app.route('/api/age_groups', methods=['GET', 'POST'])
def get_age_groups():
    if request.method == 'POST':
        data = request.json or {}
        countries = data.get('countries') or data.get('country', [])
        years = data.get('years') or data.get('year', [])
    else:
        c_param = request.args.get('countries') or request.args.get('country')
        countries = [x.strip() for x in c_param.split(',')] if c_param else []
        y_param = request.args.get('years') or request.args.get('year')
        years = [x.strip() for x in y_param.split(',')] if y_param else []
    
    if isinstance(countries, str):
        countries = [countries]
    if isinstance(years, str):
        years = [years]
        
    conds = []
    if countries and 'ALL' not in countries and len(countries) < len(COUNTRY_MAP):
        quoted = ", ".join(f"'{c}'" for c in countries)
        conds.append(f"ReportingCountry in ({quoted})")
    if years and 'ALL' not in years:
        quoted = ", ".join(f"'{y}'" for y in years)
        conds.append(f"substr(YearWeekISO, 1, 4) in ({quoted})")
        
    where_clause = ("where " + " and ".join(conds)) if conds else ""
    
    if ensure_sas_ready():
        code = f"""
        proc sql;
            create table work.ages as
            select distinct TargetGroup
            from work.covid_vaccine
            {where_clause}
            order by TargetGroup;
        quit;
        """
        with sas_lock:
            sas.submit(code)
            res_df = sas.sd2df("ages", libref="work")
        ages = res_df['TargetGroup'].tolist()
    else:
        if df_sub is not None:
            sub = df_sub
            if countries and 'ALL' not in countries:
                sub = sub[sub['ReportingCountry'].isin(countries)]
            if years and 'ALL' not in years:
                sub = sub[sub['YearWeekISO'].str[:4].isin(years)]
            ages = sorted(sub['TargetGroup'].unique().tolist())
        else:
            ages = []
    
    result = [{'code': a, 'name': AGE_MAP.get(a, a)} for a in ages]
    result = sorted(result, key=lambda x: (0 if x['code'] == 'ALL' else 1, x['name']))
    return jsonify(result)

@app.route('/api/vtv/diseases', methods=['GET'])
def get_vtv_diseases():
    unique_diseases = []
    if ensure_sas_ready() and ensure_vtv_sas_tables():
        with sas_lock:
            sas.submit("""
            proc sql;
                create table work.vtv_dis_list as
                select distinct Disease_Name
                from work.vtv_dalys
                where Disease_Name ne 'All Causes (Total)'
                order by Disease_Name;
            quit;
            """)
            res_df = sas.sd2df("vtv_dis_list", libref="work")
            if res_df is not None and not res_df.empty:
                unique_diseases = res_df['Disease_Name'].dropna().tolist()

    if not unique_diseases:
        if df_vtv is not None and 'Disease_Name' in df_vtv.columns:
            unique_diseases = sorted([d for d in df_vtv['Disease_Name'].unique() if d != 'All Causes (Total)'])
        else:
            unique_diseases = [d for d in VTV_DISEASE_MAP.keys() if d not in ('ALL', 'All Causes (Total)')]

    result = [{'code': 'ALL', 'name': 'All Disease Groups & Conditions (Total Combined + Breakdown)', 'category': 'Master Aggregate'}]
    for d in unique_diseases:
        result.append({
            'code': d,
            'name': VTV_DISEASE_MAP.get(d, d),
            'category': 'Specific Condition'
        })
    result.append({
        'code': 'All Causes (Total)',
        'name': 'All Causes (Total Inpatient Morbidity & Mortality)',
        'category': 'Master Aggregate'
    })
    return jsonify(result)

@app.route('/api/vtv/years', methods=['GET', 'POST'])
def get_vtv_years():
    years = [
        {'code': 'ALL', 'name': 'All Observed & Projected Horizons (2020–2050)'},
        {'code': '2020', 'name': '2020 (Observed Empirical Baseline)'},
        {'code': '2021', 'name': '2021 (Observed Surveillance)'},
        {'code': '2022', 'name': '2022 (VTV Baseline Year)'},
        {'code': '2023', 'name': '2023 (Recent Observed Surveillance)'},
        {'code': '2030', 'name': '2030 (VTV Trendscenario Projection)'},
        {'code': '2040', 'name': '2040 (VTV Mid-Horizon Projection)'},
        {'code': '2050', 'name': '2050 (VTV Long-Horizon Projection)'}
    ]
    return jsonify(years)

@app.route('/api/vtv/strata', methods=['GET', 'POST'])
def get_vtv_strata():
    genders = [
        {'code': 'Both Sexes', 'name': 'Both Sexes (Total Combined)'},
        {'code': 'Male', 'name': 'Men (Male)'},
        {'code': 'Female', 'name': 'Women (Female)'}
    ]
    age_strata = [
        {'code': 'ALL', 'name': 'All Age Strata (Total Population + Age Breakdown)'},
        {'code': '<15', 'name': 'Under 15 years (<15)'},
        {'code': '15-24', 'name': '15 – 24 years old'},
        {'code': '25-44', 'name': '25 – 44 years old'},
        {'code': '45-64', 'name': '45 – 64 years old'},
        {'code': '65-74', 'name': '65 – 74 years old'},
        {'code': '75+', 'name': '75+ years old'},
        {'code': 'Total', 'name': 'Total Population Aggregate'}
    ]
    metrics = [
        {'code': 'DALY', 'name': 'DALY (Disability-Adjusted Life Years = YLL + YLD)'},
        {'code': 'YLL', 'name': 'YLL (Years of Life Lost - Premature Mortality)'},
        {'code': 'YLD', 'name': 'YLD (Years Lived with Disability - Non-fatal Morbidity)'},
        {'code': 'Inpatient_Rate_Per10k', 'name': 'Inpatient Hospital Admission Rate (per 10,000)'},
        {'code': 'Inpatient_Admissions', 'name': 'Total Hospital Inpatient Admissions'}
    ]
    return jsonify({'genders': genders, 'age_strata': age_strata, 'metrics': metrics})

def generate_vtv_report(data):
    diseases = data.get('diseases') or data.get('disease') or ['ALL']
    if isinstance(diseases, str):
        diseases = [diseases]
    years = data.get('years') or data.get('year') or ['ALL']
    if isinstance(years, str):
        years = [years]
    gender = data.get('gender') or data.get('genders') or 'Both Sexes'
    if isinstance(gender, list):
        gender = gender[0] if gender else 'Both Sexes'
    age_strata = data.get('age_strata') or data.get('ages') or ['ALL']
    if isinstance(age_strata, str):
        age_strata = [age_strata]
    metric = data.get('metric') or 'DALY'
    if metric not in VTV_METRIC_MAP:
        metric = 'DALY'
    selected_style = (data.get('style') or 'nature').lower()

    all_diseases_selected = ('ALL' in diseases) or (len(diseases) >= 15)
    all_years_selected = ('ALL' in years) or (len(years) >= 7)
    all_ages_selected = ('ALL' in age_strata) or (len(age_strata) >= 7)

    # Human-readable labels
    if all_diseases_selected:
        disease_label = "All Disease Groups (N=16 Conditions)"
        disease_slug = "ALL_DISEASES"
    elif len(diseases) == 1:
        disease_label = VTV_DISEASE_MAP.get(diseases[0], diseases[0])
        disease_slug = diseases[0][:15].replace(' ', '_').replace('&', 'and')
    else:
        disease_label = f"{len(diseases)} Selected Conditions"
        disease_slug = f"{len(diseases)}_diseases"

    if all_years_selected:
        year_label = "All Horizons (2020–2050)"
        year_slug = "ALL_YEARS"
    elif len(years) == 1:
        year_label = str(years[0])
        year_slug = str(years[0]).split()[0]
    else:
        year_label = ", ".join(str(y).split()[0] for y in years)
        year_slug = "_".join(str(y).split()[0] for y in years)

    if all_ages_selected:
        age_label = "All Age Strata (Total + Breakdown)"
        age_slug = "ALL_AGES"
    elif len(age_strata) == 1:
        age_label = str(age_strata[0])
        age_slug = str(age_strata[0]).replace('<', 'lt').replace('>', 'gt').replace('+', 'plus')
    else:
        age_label = f"{len(age_strata)} Age Strata Selected"
        age_slug = f"{len(age_strata)}_ages"

    metric_name = VTV_METRIC_MAP.get(metric, metric)

    if selected_style == 'ecology':
        sas_style = 'styles.EcologyJournal'
        style_title = 'Ecology Journal Publication Standard'
        theme_primary = '#2c5e3b'
        theme_secondary = '#8c6239'
    elif selected_style == 'sapphire':
        sas_style = 'styles.Sapphire'
        style_title = 'Clinical Sapphire Standard'
        theme_primary = '#0284c7'
        theme_secondary = '#475569'
    else:
        sas_style = 'styles.NatureJournal'
        style_title = 'Nature Journal Publication Standard'
        theme_primary = '#1a1a1a'
        theme_secondary = '#2563eb'

    style_suffix = f"_{selected_style}" if selected_style != 'nature' else ""
    report_filename = f"report_vtv_{disease_slug}_{year_slug}_{age_slug}_{metric}{style_suffix}.pdf".replace('<', 'lt').replace('>', 'gt').replace('+', 'plus')
    report_filepath = os.path.join(REPORTS_DIR, report_filename)

    if ensure_sas_ready() and ensure_vtv_sas_tables():
        # Build SQL filter conditions for SAS
        conds = []
        if not all_diseases_selected:
            conds.append(f"Disease_Name in ({', '.join(repr(d) for d in diseases)})")
        else:
            conds.append("Disease_Name ne 'All Causes (Total)'")
            
        clean_years = [str(y).split()[0] for y in years if str(y).split()[0].isdigit()]
        obs_years = [y for y in clean_years if int(y) in (2020, 2021, 2022, 2023)]
        if not all_years_selected and obs_years:
            conds.append(f"Year in ({', '.join(obs_years)})")
            
        if gender and gender != 'Both Sexes':
            conds.append(f"Gender = {repr(gender)}")
        else:
            conds.append("Gender = 'Both Sexes'")
            
        if not all_ages_selected:
            conds.append(f"Age_Stratum in ({', '.join(repr(a) for a in age_strata)})")
            
        where_base = ("where " + " and ".join(conds)) if conds else ""

        # Disease comparison condition
        dis_conds = [c for c in conds if not c.startswith("Disease_Name")]
        if not all_diseases_selected:
            specific_d = [d for d in diseases if d != 'All Causes (Total)']
            if specific_d:
                dis_conds.append(f"Disease_Name in ({', '.join(repr(d) for d in specific_d)})")
            else:
                dis_conds.append(f"Disease_Name in ({', '.join(repr(d) for d in diseases)})")
        else:
            dis_conds.append("Disease_Name ne 'All Causes (Total)'")
        where_dis = ("where " + " and ".join(dis_conds)) if dis_conds else ""

        # Age strata condition
        age_conds = [c for c in conds if not c.startswith("Age_Stratum")]
        if not all_ages_selected:
            age_conds.append(f"Age_Stratum in ({', '.join(repr(a) for a in age_strata)})")
        else:
            age_conds.append("Age_Stratum in ('<15', '15-24', '25-44', '45-64', '65-74', '75+')")
        where_age_strata = ("where " + " and ".join(age_conds)) if age_conds else ""

        agg_metric = "mean" if "Rate" in metric else "sum"
        metric_fmt = "8.2" if "Rate" in metric else "comma12."

        sas_vtv_code = f"""
        options nodate nonumber linesize=132 pagesize=90;
        title; footnote;

        proc template;
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
                    linethickness = 1.8px;
                class GraphData1 / contrastcolor=cx1A1A1A color=cx1A1A1A;
                class GraphData2 / contrastcolor=cx2563EB color=cx2563EB;
                class GraphData3 / contrastcolor=cxE64B35 color=cxE64B35;
                class GraphData4 / contrastcolor=cx00A087 color=cx00A087;
            end;

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
                    linethickness = 1.8px;
                class GraphData1 / contrastcolor=cx2C5E3B color=cx2C5E3B;
                class GraphData2 / contrastcolor=cx8C6239 color=cx8C6239;
                class GraphData3 / contrastcolor=cx2B547E color=cx2B547E;
            end;

            define style styles.Sapphire;
                parent = styles.listing;
                class GraphFonts /
                    'GraphTitleFont'    = ("Arial, Helvetica, sans-serif", 10.5pt, bold)
                    'GraphLabelFont'    = ("Arial, Helvetica, sans-serif", 9pt, bold)
                    'GraphValueFont'    = ("Arial, Helvetica, sans-serif", 8pt)
                    'GraphDataFont'     = ("Arial, Helvetica, sans-serif", 7.5pt)
                    'GraphFootnoteFont' = ("Arial, Helvetica, sans-serif", 7.5pt, italic);
                class GraphColors /
                    'gaxis' = cx0F172A
                    'ggrid' = cxf1f5f9
                    'gback' = cxffffff;
                class GraphWalls /
                    frameborder = off
                    backgroundcolor = cxffffff;
                class GraphDataDefault /
                    markersize = 7px
                    linethickness = 1.8px;
                class GraphData1 / contrastcolor=cx0284C7 color=cx0284C7;
                class GraphData2 / contrastcolor=cx475569 color=cx475569;
                class GraphData3 / contrastcolor=cx0369A1 color=cx0369A1;
            end;
        run;

        %let workpath = %sysfunc(pathname(work));
        filename vtvpdf "&workpath/vtv_report.pdf";

        ods graphics / reset width=7.4in height=4.5in noborder;
        ods pdf file=vtvpdf notoc style={sas_style} dpi=300;

        /* 1. Longitudinal Trajectory Transformation & Labeling */
        proc sql;
            create table work.vtv_rep_trend as
            select Year,
                   {agg_metric}({metric}) as MetricTotal,
                   sum(YLL) as TotalYLL,
                   sum(YLD) as TotalYLD,
                   sum(Inpatient_Admissions) as TotalAdmissions
            from work.vtv_dalys
            {where_base}
            group by Year
            order by Year;
        quit;

        data work.vtv_rep_trend;
            set work.vtv_rep_trend;
            label Year = "Calendar Horizon Year"
                  MetricTotal = "{metric_name}"
                  TotalYLL = "Years of Life Lost (Mortality)"
                  TotalYLD = "Years Lived with Disability (Morbidity)"
                  TotalAdmissions = "Inpatient Hospital Admissions";
            format MetricTotal {metric_fmt} TotalYLL TotalYLD TotalAdmissions comma12.;
        run;

        proc sgplot data=work.vtv_rep_trend;
            title "Figure 1 | Longitudinal Disease Burden Trajectory ({metric_name})";
            title2 "{style_title} | Conditions: {disease_label} | Horizon: {year_label} | Stratification: {gender}";
            footnote1 italic "Figure 1 Note: Total {metric_name} aggregated across selected conditions. Linked to Table 1.";
            footnote2 italic "Source: RIVM VTV-2024 Trendscenario (https://www.volksgezondheidtoekomstverkenning.nl/vtv-2024/trendscenario)";
            series x=Year y=MetricTotal / lineattrs=(thickness=2.2px) datalabel markers markerattrs=(symbol=circlefilled size=7);
            refline 2022 / axis=x lineattrs=(pattern=shortdash color=gray) label="2022 Baseline";
            xaxis label="Calendar Horizon Year" grid;
            yaxis label="{metric_name}" grid;
        run;

        /* 2. Disease Comparison Transformation, Ranking & Labeling */
        proc sql;
            create table work.vtv_rep_dis_raw as
            select Disease_Name,
                   {agg_metric}({metric}) as MetricTotal,
                   sum(YLL) as TotalYLL,
                   sum(YLD) as TotalYLD
            from work.vtv_dalys
            {where_dis}
            group by Disease_Name
            order by MetricTotal desc;
        quit;

        data work.vtv_rep_dis;
            set work.vtv_rep_dis_raw;
            disease_rank = _N_;
            if TotalYLL + TotalYLD > 0 then yll_share_pct = round((TotalYLL / (TotalYLL + TotalYLD)) * 100, 0.1);
            else yll_share_pct = 0;
            label disease_rank = "Rank"
                  Disease_Name = "Disease / Health Condition"
                  MetricTotal = "{metric_name}"
                  TotalYLL = "Years of Life Lost (Mortality)"
                  TotalYLD = "Years Lived with Disability (Morbidity)"
                  yll_share_pct = "Mortality Share (%)";
            format MetricTotal {metric_fmt} TotalYLL TotalYLD comma12. yll_share_pct 5.1;
        run;

        proc sgplot data=work.vtv_rep_dis;
            title "Figure 2 | Disease Group Comparison & Relative Contribution ({metric_name})";
            title2 "{style_title} | Linked to Table 2";
            footnote1 italic "Figure 2 Note: Disease categories ranked by {metric_name}. Linked to Table 2.";
            hbar Disease_Name / response=MetricTotal categoryorder=respasc datalabel;
            xaxis label="{metric_name}" grid;
            yaxis label="" discreteorder=data;
        run;

        /* 3. Age-Stratified Distribution Transformation & Labeling */
        proc sql;
            create table work.vtv_rep_age as
            select Age_Stratum,
                   {agg_metric}({metric}) as MetricTotal,
                   sum(YLL) as TotalYLL,
                   sum(YLD) as TotalYLD
            from work.vtv_dalys
            {where_age_strata}
            group by Age_Stratum
            order by Age_Stratum;
        quit;

        data work.vtv_rep_age;
            set work.vtv_rep_age;
            label Age_Stratum = "Age Cohort Stratum"
                  MetricTotal = "{metric_name}"
                  TotalYLL = "Years of Life Lost (YLL)"
                  TotalYLD = "Years Lived with Disability (YLD)";
            format MetricTotal {metric_fmt} TotalYLL TotalYLD comma12.;
        run;

        proc sgplot data=work.vtv_rep_age;
            title "Figure 3 | Age-Stratified Distribution & Epidemiological Transition ({metric_name})";
            title2 "{style_title} | Linked to Table 3";
            footnote1 italic "Figure 3 Note: Burden concentration across youth, working-age, and elderly cohorts. Linked to Table 3.";
            vbar Age_Stratum / response=MetricTotal datalabel;
            xaxis label="Age Cohort Stratum" grid;
            yaxis label="{metric_name}" grid;
        run;

        /* 4. Linked Summary Tables Generated via PROC REPORT */
        proc report data=work.vtv_rep_trend nowd split='*';
            title "Table 1 (Linked to Figure 1): Annual Disease Burden Trajectory";
            title2 "Temporal evolution of {metric_name} across selected observed and projected horizons";
            column Year MetricTotal TotalYLL TotalYLD TotalAdmissions;
            define Year / "Calendar*Year" style(column)={{justification=c width=15%}};
            define MetricTotal / "{metric_name}" format={metric_fmt} style(column)={{justification=r width=25%}};
            define TotalYLL / "Years of Life Lost*(Mortality)" format=comma12. style(column)={{justification=r width=20%}};
            define TotalYLD / "Years Lived with*Disability" format=comma12. style(column)={{justification=r width=20%}};
            define TotalAdmissions / "Inpatient*Admissions" format=comma12. style(column)={{justification=r width=20%}};
        run;

        proc report data=work.vtv_rep_dis nowd split='*';
            title "Table 2 (Linked to Figure 2): Disease Group Rankings & Burden Volume";
            title2 "Cross-condition ranking and distribution of {metric_name} across VTV taxonomy";
            column disease_rank Disease_Name MetricTotal TotalYLL yll_share_pct;
            define disease_rank / "Rank" style(column)={{justification=c width=8%}};
            define Disease_Name / "Disease / Health Condition" style(column)={{width=42%}};
            define MetricTotal / "{metric_name}" format={metric_fmt} style(column)={{justification=r width=20%}};
            define TotalYLL / "YLL (Mortality)" format=comma12. style(column)={{justification=r width=15%}};
            define yll_share_pct / "Mortality*Share (%)" format=5.1 style(column)={{justification=r width=15%}};
        run;

        proc report data=work.vtv_rep_age nowd split='*';
            title "Table 3 (Linked to Figure 3): Age-Stratified Distribution & Epidemiological Transition";
            title2 "Burden concentration across youth (<15, 15-24), working-age (25-64), and senior cohorts (65-74, 75+)";
            column Age_Stratum MetricTotal TotalYLL TotalYLD;
            define Age_Stratum / "Age Stratum" style(column)={{justification=c width=25%}};
            define MetricTotal / "{metric_name}" format={metric_fmt} style(column)={{justification=r width=25%}};
            define TotalYLL / "Years of Life Lost (YLL)" format=comma12. style(column)={{justification=r width=25%}};
            define TotalYLD / "Years Lived with Disability (YLD)" format=comma12. style(column)={{justification=r width=25%}};
        run;

        ods pdf close;
        """

        with sas_lock:
            sas.submit(sas_vtv_code)
            workpath = sas.symget('workpath').strip()
            remote_pdf = f"{workpath}/vtv_report.pdf"
            sas.download(report_filepath, remote_pdf)

    else:
        # Subsetting logic
        sub = df_vtv.copy() if df_vtv is not None else pd.DataFrame()
        if not sub.empty:
            if not all_diseases_selected:
                sub = sub[sub['Disease_Name'].isin(diseases)]
            if not all_years_selected:
                clean_years = [str(y).split()[0] for y in years]
                sub = sub[sub['Year'].astype(str).isin(clean_years)]
            if gender and gender != 'Both Sexes' and 'Gender' in sub.columns:
                sub = sub[sub['Gender'] == gender]
            elif 'Gender' in sub.columns and not ('Gender' in (data.get('stratify_by') or [])):
                sub = sub[sub['Gender'] == 'Both Sexes']
            if not all_ages_selected and 'Age_Stratum' in sub.columns:
                sub = sub[sub['Age_Stratum'].isin(age_strata)]

        # Matplotlib High-Resolution Publication Fallback PDF
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        from matplotlib.backends.backend_pdf import PdfPages

        with PdfPages(report_filepath) as pdf:
            # 1. Page 1: Figure 1 Longitudinal Trajectory
            fig1, ax1 = plt.subplots(figsize=(10, 6), dpi=300)
            ax1.spines['top'].set_visible(False)
            ax1.spines['right'].set_visible(False)
            if not sub.empty and 'Year' in sub.columns and metric in sub.columns:
                trend_df = sub.groupby('Year')[metric].sum().reset_index()
                ax1.plot(trend_df['Year'].astype(str), trend_df[metric], marker='o', linewidth=2.4, color=theme_secondary, label=f"Total {metric}")
                for _, r in trend_df.iterrows():
                    val_str = f"{r[metric]:,.0f}" if r[metric] >= 100 else f"{r[metric]:.1f}"
                    ax1.annotate(val_str, (str(r['Year']), r[metric]), textcoords="offset points", xytext=(0, 7), ha='center', fontsize=8, fontweight='semibold')
            ax1.set_title(f"Figure 1 | Longitudinal Disease Burden Trajectory ({metric_name})\n{style_title} | Conditions: {disease_label} | Horizon: {year_label} | Stratification: {gender}", fontsize=11, fontweight='bold', pad=12)
            ax1.set_xlabel("Calendar Horizon Year", fontsize=9, fontweight='semibold')
            ax1.set_ylabel(metric_name, fontsize=9, fontweight='semibold')
            ax1.grid(True, linestyle='--', alpha=0.5)
            ax1.legend(loc='best', frameon=False, fontsize=8.5)
            plt.tight_layout()
            pdf.savefig(fig1)
            plt.close(fig1)

            # 2. Page 2: Figure 2 Disease Condition Comparison
            fig2, ax2 = plt.subplots(figsize=(10, 6.5), dpi=300)
            ax2.spines['top'].set_visible(False)
            ax2.spines['right'].set_visible(False)
            if not sub.empty and 'Disease_Name' in sub.columns and metric in sub.columns:
                dis_df = sub[sub['Disease_Name'] != 'All Causes (Total)'].groupby('Disease_Name')[metric].sum().reset_index()
                dis_df = dis_df.sort_values(by=metric, ascending=True)
                y_pos = range(len(dis_df))
                ax2.barh(y_pos, dis_df[metric], color=theme_primary, alpha=0.85, height=0.6)
                ax2.set_yticks(y_pos)
                ax2.set_yticklabels([VTV_DISEASE_MAP.get(n, n)[:36] for n in dis_df['Disease_Name']], fontsize=8)
                for i, v in enumerate(dis_df[metric]):
                    val_str = f" {v:,.0f}" if v >= 100 else f" {v:.1f}"
                    ax2.text(v, i, val_str, va='center', fontsize=7.5, fontweight='semibold')
            ax2.set_title(f"Figure 2 | Disease Group Comparison & Relative Contribution ({metric_name})\n{style_title} | Linked to Table 2", fontsize=11, fontweight='bold', pad=12)
            ax2.set_xlabel(metric_name, fontsize=9, fontweight='semibold')
            ax2.grid(True, linestyle='--', alpha=0.5, axis='x')
            plt.tight_layout()
            pdf.savefig(fig2)
            plt.close(fig2)

            # 3. Page 3: Figure 3 Age Stratum Gradient & Linked Summary Tables
            fig3, ax3 = plt.subplots(figsize=(10, 6.5), dpi=300)
            ax3.axis('off')
            ax3.text(0.04, 0.94, "Executive Summary Table: Dutch PHFS Disease Burden Analysis", fontsize=11, fontweight='bold')
            ax3.text(0.04, 0.89, f"Conditions: {disease_label} | Surveillance: {year_label} | Strata: {gender} ({age_label}) | Metric: {metric_name}", fontsize=8.5, color='#475569')

            ax3.text(0.04, 0.78, "Table 1 (Linked to Figure 1): Annual Disease Burden Trajectory", fontsize=10, fontweight='bold')
            ax3.text(0.04, 0.72, f"Temporal evolution of {metric_name} across selected observed and projected horizons", fontsize=8, color='#475569')

            ax3.text(0.04, 0.56, "Table 2 (Linked to Figure 2): Disease Group Rankings & Burden Volume", fontsize=10, fontweight='bold')
            ax3.text(0.04, 0.50, f"Cross-condition ranking and distribution of {metric_name} across VTV taxonomy", fontsize=8, color='#475569')

            ax3.text(0.04, 0.34, "Table 3 (Linked to Figure 3): Age-Stratified Distribution & Epidemiological Transition", fontsize=10, fontweight='bold')
            ax3.text(0.04, 0.28, "Burden concentration across youth (<15, 15-24), working-age (25-64), and senior cohorts (65-74, 75+)", fontsize=8, color='#475569')

            ax3.text(0.04, 0.12, "Strategic RIVM VTV Note: Replicates official findings from https://www.volksgezondheidtoekomstverkenning.nl/vtv-2024/trendscenario", fontsize=8, fontstyle='italic', color='#64748b')

            plt.tight_layout()
            pdf.savefig(fig3)
            plt.close(fig3)

    return jsonify({"report_url": url_for('static', filename=f'reports/{report_filename}')})

@app.route('/api/vtv/report', methods=['POST'])
def generate_vtv_report_route():
    data = request.json or {}
    return generate_vtv_report(data)

@app.route('/api/report', methods=['POST'])
def generate_report():
    data = request.json or {}
    if data.get('dataset') == 'cbs-vtv-phfs' or data.get('dataset_id') == 'cbs-vtv-phfs':
        return generate_vtv_report(data)
    data = request.json or {}
    countries = data.get('countries') or data.get('country') or ['ALL']
    if isinstance(countries, str):
        countries = [countries]
    years = data.get('years') or data.get('year') or ['ALL']
    if isinstance(years, str):
        years = [years]
    ages = data.get('ages') or data.get('age') or ['ALL']
    if isinstance(ages, str):
        ages = [ages]
    
    all_countries_selected = ('ALL' in countries) or (len(countries) >= len(COUNTRY_MAP))
    all_years_selected = ('ALL' in years)
    all_ages_selected = ('ALL' in ages)
    
    # Human-readable labels
    if all_countries_selected:
        country_label = "All EU/EEA Countries"
        country_slug = "ALL_COUNTRIES"
    elif len(countries) == 1:
        country_label = f"{COUNTRY_MAP.get(countries[0], countries[0])} ({countries[0]})"
        country_slug = countries[0]
    elif len(countries) <= 3:
        country_label = ", ".join(f"{COUNTRY_MAP.get(c, c)} ({c})" for c in countries)
        country_slug = "_".join(countries)
    else:
        country_label = f"{len(countries)} Selected Countries (" + ", ".join(countries[:3]) + "...)"
        country_slug = f"{len(countries)}_countries"

    if all_years_selected:
        year_label = "All Available Years"
        year_slug = "ALL_YEARS"
    elif len(years) == 1:
        year_label = years[0]
        year_slug = years[0]
    else:
        year_label = ", ".join(years)
        year_slug = "_".join(years)

    if all_ages_selected:
        age_label = "All Ages (Total Line + Age Breakdown)"
        age_slug = "ALL_AGES"
    elif len(ages) == 1:
        age_label = AGE_MAP.get(ages[0], ages[0])
        age_slug = ages[0]
    else:
        age_label = f"{len(ages)} Age Groups Selected"
        age_slug = f"{len(ages)}_ages"

    selected_style = (data.get('style') or 'nature').lower()
    if selected_style == 'ecology':
        sas_style = 'styles.EcologyJournal'
        style_title = 'Ecology Journal Publication Standard'
    elif selected_style == 'sapphire':
        sas_style = 'styles.Sapphire'
        style_title = 'Clinical Sapphire Standard'
    else:
        sas_style = 'styles.NatureJournal'
        style_title = 'Nature Journal Publication Standard'

    style_suffix = f"_{selected_style}" if selected_style != 'nature' else ""
    report_filename = f"report_{country_slug}_{year_slug}_{age_slug}{style_suffix}.pdf".replace('<', 'lt').replace('>', 'gt').replace('+', 'plus')
    report_filepath = os.path.join(REPORTS_DIR, report_filename)

    # Build SQL filter fragments
    cond_country = "" if all_countries_selected else f"ReportingCountry in ({', '.join(repr(c) for c in countries)})"
    cond_year = "" if all_years_selected else f"substr(YearWeekISO, 1, 4) in ({', '.join(repr(y) for y in years)})"
    
    base_conds = [c for c in [cond_country, cond_year] if c]
    
    # Filter for age breakdown plot
    if all_ages_selected:
        cond_age = "TargetGroup in ('ALL', 'Age<18', 'Age18_24', 'Age25_49', 'Age50_59', 'Age60_69', 'Age70_79', 'Age80+')"
    else:
        cond_age = f"TargetGroup in ({', '.join(repr(a) for a in ages)})"
        
    where_age = ("where " + " and ".join(base_conds + [cond_age])) if (base_conds or cond_age) else ""
    
    # Filter for totals (scatterplot)
    if all_ages_selected or 'ALL' in ages:
        where_totals = ("where " + " and ".join(base_conds + ["TargetGroup = 'ALL'"]))
    else:
        where_totals = ("where " + " and ".join(base_conds + [f"TargetGroup in ({', '.join(repr(a) for a in ages)})"]))

    # Country plot needed if multiple countries or All Countries selected
    show_country_plot = all_countries_selected or len(countries) > 1
    where_cntry = ("where " + " and ".join(base_conds + ["TargetGroup = 'ALL'"]))

    if ensure_sas_ready():
        sas_code = f"""
        proc template;
            /* 1. Nature Journal Style Template */
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
                class GraphData1 / contrastcolor=cx1A1A1A color=cx1A1A1A;
                class GraphData2 / contrastcolor=cx737373 color=cx737373;
                class GraphData3 / contrastcolor=cxE64B35 color=cxE64B35;
                class GraphData4 / contrastcolor=cx00A087 color=cx00A087;
                class GraphData5 / contrastcolor=cx3C5488 color=cx3C5488;
                class GraphData6 / contrastcolor=cxF39B7F color=cxF39B7F;
                class GraphData7 / contrastcolor=cx8491B4 color=cx8491B4;
                class GraphData8 / contrastcolor=cx91D1C2 color=cx91D1C2;
            end;

            /* 2. Ecology Journal Style Template */
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
                class GraphData1 / contrastcolor=cx2C5E3B color=cx2C5E3B;
                class GraphData2 / contrastcolor=cx8C6239 color=cx8C6239;
                class GraphData3 / contrastcolor=cx2B547E color=cx2B547E;
                class GraphData4 / contrastcolor=cxD4A017 color=cxD4A017;
                class GraphData5 / contrastcolor=cx556B2F color=cx556B2F;
                class GraphData6 / contrastcolor=cx708090 color=cx708090;
            end;
        run;

        %let workpath = %sysfunc(pathname(work));
        filename mypdf "&workpath/report.pdf";
        
        ods graphics / reset width=7.2in height=4.4in noborder;
        ods pdf file=mypdf notoc style={sas_style} dpi=300;
        
        title "COVID-19 Vaccine Intake Comprehensive Report";
        title2 "{style_title} | Countries: {country_label} | Years: {year_label}";
        
        /* 1. Overall Totals: Gray (First Dose) vs Black (Second Dose) Scatterplot */
        proc sql;
            create table work.rep_tot as
            select YearWeekISO,
                   sum(FirstDose) as TotalFirst,
                   sum(SecondDose) as TotalSecond,
                   sum(FirstDose + SecondDose) as TotalDoses
            from work.covid_vaccine
            {where_totals}
            group by YearWeekISO
            order by YearWeekISO;
        quit;
        
        proc sgplot data=work.rep_tot;
            title "Figure 1 | Weekly Vaccine Doses Scatterplot (First Dose: Gray, Second Dose: Black)";
            title2 "{style_title} | Linked to Table 1";
            scatter x=YearWeekISO y=TotalFirst / legendlabel="First Dose" markerattrs=(color=gray symbol=circlefilled size=8);
            scatter x=YearWeekISO y=TotalSecond / legendlabel="Second Dose" markerattrs=(color=black symbol=circlefilled size=8);
            xaxis label="Week" valuesrotate=diagonal offsetmin=0.02 offsetmax=0.02 grid;
            yaxis label="Doses Administered" grid;
            keylegend / location=outside position=top noborder;
        run;

        /* 2. Age Group Breakdown: Line for All Ages + Line for each age group */
        proc sql;
            create table work.rep_age_raw as
            select YearWeekISO, TargetGroup,
                   sum(FirstDose + SecondDose) as TotalDoses
            from work.covid_vaccine
            {where_age}
            group by YearWeekISO, TargetGroup
            order by YearWeekISO, TargetGroup;
        quit;
        
        data work.rep_age;
            set work.rep_age_raw;
            length AgeLabel $50;
            if TargetGroup = 'ALL' then AgeLabel = 'All Ages (Total)';
            else if TargetGroup = 'Age0_4' then AgeLabel = '0 - 4 years old';
            else if TargetGroup = 'Age5_9' then AgeLabel = '5 - 9 years old';
            else if TargetGroup = 'Age10_14' then AgeLabel = '10 - 14 years old';
            else if TargetGroup = 'Age15_17' then AgeLabel = '15 - 17 years old';
            else if TargetGroup = 'Age<18' then AgeLabel = 'Under 18 years old (<18)';
            else if TargetGroup = 'Age18_24' then AgeLabel = '18 - 24 years old';
            else if TargetGroup = 'Age25_49' then AgeLabel = '25 - 49 years old';
            else if TargetGroup = 'Age50_59' then AgeLabel = '50 - 59 years old';
            else if TargetGroup = 'Age60_69' then AgeLabel = '60 - 69 years old';
            else if TargetGroup = 'Age70_79' then AgeLabel = '70 - 79 years old';
            else if TargetGroup = 'Age80+' then AgeLabel = '80+ years old';
            else if TargetGroup = '1_Age<60' then AgeLabel = 'Under 60 years old (<60)';
            else if TargetGroup = '1_Age60+' then AgeLabel = '60+ years old';
            else if TargetGroup = 'HCW' then AgeLabel = 'Healthcare Workers (HCW)';
            else if TargetGroup = 'LTCF' then AgeLabel = 'Long-Term Care Facility (LTCF)';
            else if TargetGroup = 'AgeUNK' then AgeLabel = 'Unknown Age';
            else AgeLabel = TargetGroup;
        run;
        
        proc sgplot data=work.rep_age;
            title "Figure 2 | Weekly Vaccine Doses by Age Group (All Ages Total + Individual Age Groups)";
            title2 "{style_title} | Linked to Table 2";
            series x=YearWeekISO y=TotalDoses / group=AgeLabel lineattrs=(thickness=1.8);
            xaxis label="Week" valuesrotate=diagonal offsetmin=0.02 offsetmax=0.02 grid;
            yaxis label="Total Doses Administered" grid;
            keylegend / location=outside position=top across=3 noborder;
        run;
        """

        if show_country_plot:
            sas_code += f"""
            /* 3. Country Breakdown: Line for each country + Line with Total */
            proc sql;
                create table work.rep_cntry_raw as
                select YearWeekISO, ReportingCountry,
                       sum(FirstDose + SecondDose) as TotalDoses
                from work.covid_vaccine
                {where_cntry}
                group by YearWeekISO, ReportingCountry
                order by YearWeekISO, ReportingCountry;
            quit;
            
            proc sql;
                create table work.rep_cntry_tot as
                select YearWeekISO, 'ALL_TOTAL' as ReportingCountry,
                       sum(FirstDose + SecondDose) as TotalDoses
                from work.covid_vaccine
                {where_cntry}
                group by YearWeekISO;
            quit;
            
            data work.rep_cntry;
                set work.rep_cntry_raw work.rep_cntry_tot;
                length CountryLabel $50;
                if ReportingCountry = 'ALL_TOTAL' then CountryLabel = 'All Selected Countries (Total)';
                else if ReportingCountry = 'AT' then CountryLabel = 'Austria';
                else if ReportingCountry = 'BE' then CountryLabel = 'Belgium';
                else if ReportingCountry = 'BG' then CountryLabel = 'Bulgaria';
                else if ReportingCountry = 'HR' then CountryLabel = 'Croatia';
                else if ReportingCountry = 'CY' then CountryLabel = 'Cyprus';
                else if ReportingCountry = 'CZ' then CountryLabel = 'Czechia';
                else if ReportingCountry = 'DK' then CountryLabel = 'Denmark';
                else if ReportingCountry = 'EE' then CountryLabel = 'Estonia';
                else if ReportingCountry = 'FI' then CountryLabel = 'Finland';
                else if ReportingCountry = 'FR' then CountryLabel = 'France';
                else if ReportingCountry = 'DE' then CountryLabel = 'Germany';
                else if ReportingCountry = 'EL' then CountryLabel = 'Greece';
                else if ReportingCountry = 'HU' then CountryLabel = 'Hungary';
                else if ReportingCountry = 'IS' then CountryLabel = 'Iceland';
                else if ReportingCountry = 'IE' then CountryLabel = 'Ireland';
                else if ReportingCountry = 'IT' then CountryLabel = 'Italy';
                else if ReportingCountry = 'LV' then CountryLabel = 'Latvia';
                else if ReportingCountry = 'LI' then CountryLabel = 'Liechtenstein';
                else if ReportingCountry = 'LT' then CountryLabel = 'Lithuania';
                else if ReportingCountry = 'LU' then CountryLabel = 'Luxembourg';
                else if ReportingCountry = 'MT' then CountryLabel = 'Malta';
                else if ReportingCountry = 'NL' then CountryLabel = 'Netherlands';
                else if ReportingCountry = 'NO' then CountryLabel = 'Norway';
                else if ReportingCountry = 'PL' then CountryLabel = 'Poland';
                else if ReportingCountry = 'PT' then CountryLabel = 'Portugal';
                else if ReportingCountry = 'RO' then CountryLabel = 'Romania';
                else if ReportingCountry = 'SK' then CountryLabel = 'Slovakia';
                else if ReportingCountry = 'SI' then CountryLabel = 'Slovenia';
                else if ReportingCountry = 'ES' then CountryLabel = 'Spain';
                else if ReportingCountry = 'SE' then CountryLabel = 'Sweden';
                else CountryLabel = ReportingCountry;
            run;
            
            proc sgplot data=work.rep_cntry;
                title "Figure 3 | Weekly Vaccine Doses by Country (with All Countries Total Line)";
                title2 "{style_title} | Linked to Table 3";
                series x=YearWeekISO y=TotalDoses / group=CountryLabel lineattrs=(thickness=1.8);
                xaxis label="Week" valuesrotate=diagonal offsetmin=0.02 offsetmax=0.02 grid;
                yaxis label="Total Doses Administered" grid;
                keylegend / location=outside position=top across=3 noborder;
            run;
            """

        sas_code += f"""
        /* 4. Executive Summary Table */
        proc print data=work.rep_tot noobs label;
            title "Executive Summary Table: Overall Weekly Vaccine Intake";
            title2 "Aggregated totals across all selected countries, years, and target groups";
            var YearWeekISO TotalFirst TotalSecond TotalDoses;
            label YearWeekISO="Week" TotalFirst="First Doses" TotalSecond="Second Doses" TotalDoses="Total Doses";
        run;

        /* Table 1: Linked to Figure 1 */
        proc print data=work.rep_tot noobs label;
            title "Table 1 (Linked to Figure 1): First vs. Second Dose Administrations";
            title2 "Tabular data for Figure 1 scatterplot (Gray = First Dose, Black = Second Dose)";
            var YearWeekISO TotalFirst TotalSecond TotalDoses;
            label YearWeekISO="Week" TotalFirst="First Doses (Gray)" TotalSecond="Second Doses (Black)" TotalDoses="Total Doses";
        run;

        /* Table 2: Linked to Figure 2 */
        proc print data=work.rep_age noobs label;
            title "Table 2 (Linked to Figure 2): Weekly Administrations by Age Target Group";
            title2 "Tabular data for Figure 2 line chart (All Ages Total + Individual Age Groups)";
            var YearWeekISO AgeLabel TotalDoses;
            label YearWeekISO="Week" AgeLabel="Age Target Group" TotalDoses="Total Doses Administered";
        run;
        """

        if show_country_plot:
            sas_code += f"""
            /* Table 3: Linked to Figure 3 */
            proc print data=work.rep_cntry noobs label;
                title "Table 3 (Linked to Figure 3): Weekly Administrations by Reporting Country";
                title2 "Tabular data for Figure 3 line chart (All Countries Total + Individual Countries)";
                var YearWeekISO CountryLabel TotalDoses;
                label YearWeekISO="Week" CountryLabel="Reporting Country" TotalDoses="Total Doses Administered";
            run;
            """

        sas_code += """
        ods pdf close;
        """
        with sas_lock:
            sas.submit(sas_code)
            workpath = sas.symget('workpath').strip()
            remote_pdf = f"{workpath}/report.pdf"
            sas.download(report_filepath, remote_pdf)
            
    else:
        # Fallback using matplotlib
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        from matplotlib.backends.backend_pdf import PdfPages
        
        sub = df_sub if df_sub is not None else pd.DataFrame()
        if not all_countries_selected and not sub.empty:
            sub = sub[sub['ReportingCountry'].isin(countries)]
        if not all_years_selected and not sub.empty:
            sub = sub[sub['YearWeekISO'].str[:4].isin(years)]
            
        df_rep = sub.groupby('YearWeekISO')[['FirstDose', 'SecondDose']].sum().reset_index() if not sub.empty else pd.DataFrame(columns=['YearWeekISO', 'FirstDose', 'SecondDose'])
        
        with PdfPages(report_filepath) as pdf:
            # Page 1: Figure 1 Scatterplot
            fig1, ax1 = plt.subplots(figsize=(10, 6))
            ax1.scatter(df_rep['YearWeekISO'], df_rep['FirstDose'], color='gray', label='First Dose', s=50, alpha=0.85)
            ax1.scatter(df_rep['YearWeekISO'], df_rep['SecondDose'], color='black', label='Second Dose', s=50, alpha=0.85)
            ax1.set_title(f"Figure 1 | COVID-19 Vaccine Intake Scatterplot\nCountries: {country_label} | Years: {year_label} | Target Groups: {age_label}", fontsize=11, fontweight='bold')
            ax1.set_xlabel("Week")
            ax1.set_ylabel("Doses Administered")
            ax1.tick_params(axis='x', rotation=45)
            ax1.legend(loc='upper right')
            ax1.grid(True, linestyle='--', alpha=0.6)
            plt.tight_layout()
            pdf.savefig(fig1)
            plt.close(fig1)

            # Page 2: Figure 2 by Age Group
            fig2, ax2 = plt.subplots(figsize=(10, 6))
            if 'TargetGroup' in sub.columns and not sub.empty:
                age_grp = sub.groupby(['YearWeekISO', 'TargetGroup'])[['FirstDose', 'SecondDose']].sum().reset_index()
                age_grp['TotalDoses'] = age_grp['FirstDose'] + age_grp['SecondDose']
                for grp_name, grp_df in age_grp.groupby('TargetGroup'):
                    label_name = AGE_MAP.get(grp_name, grp_name)
                    ax2.plot(grp_df['YearWeekISO'], grp_df['TotalDoses'], marker='o', markersize=3, label=label_name)
                ax2.legend(loc='upper left', bbox_to_anchor=(1, 1), fontsize=7)
            ax2.set_title("Figure 2 | Weekly Vaccine Doses by Age Group\nLinked to Table 2", fontsize=11, fontweight='bold')
            ax2.set_xlabel("Week")
            ax2.set_ylabel("Total Doses Administered")
            ax2.tick_params(axis='x', rotation=45)
            ax2.grid(True, linestyle='--', alpha=0.6)
            plt.tight_layout()
            pdf.savefig(fig2)
            plt.close(fig2)

            # Page 3: Linked Tables & Summary Table
            fig3, ax3 = plt.subplots(figsize=(10, 6))
            ax3.axis('off')
            ax3.text(0.05, 0.92, "Executive Summary Table: Overall Weekly Vaccine Intake", fontsize=11, fontweight='bold')
            ax3.text(0.05, 0.85, f"Aggregated totals across selected cohort: {country_label} | {year_label}", fontsize=9, color='#475569')
            ax3.text(0.05, 0.72, "Table 1 (Linked to Figure 1): First vs. Second Dose Administrations", fontsize=10, fontweight='bold')
            ax3.text(0.05, 0.65, "Tabular values for weekly administrations (First Dose: Gray, Second Dose: Black)", fontsize=8.5, color='#475569')
            ax3.text(0.05, 0.50, "Table 2 (Linked to Figure 2): Weekly Administrations by Age Target Group", fontsize=10, fontweight='bold')
            ax3.text(0.05, 0.43, "Tabular breakdowns by age cohort and demographic strata", fontsize=8.5, color='#475569')
            plt.tight_layout()
            pdf.savefig(fig3)
            plt.close(fig3)

    return jsonify({"report_url": url_for('static', filename=f'reports/{report_filename}')})

if __name__ == '__main__':
    app.run(debug=False, port=5000)
