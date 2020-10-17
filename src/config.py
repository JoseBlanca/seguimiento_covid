
from pathlib import Path

HOME_DIR = Path.home()

BASE_DIR = HOME_DIR / 'devel/covid_situation/'

PLOT_DIR = BASE_DIR / 'plots'
HTML_REPORTS_DIR = BASE_DIR / 'reports'

DOWNLOADS_DIR = BASE_DIR / 'downloaded_reports'

MINISTRY_REPORTS_DIR = DOWNLOADS_DIR / 'ministry_reports'
DECEASED_EXCEL_DIR = DOWNLOADS_DIR / 'ministry_deceased_excel'
CCAA_CSV_DIR = DOWNLOADS_DIR / 'carlos_iii_ccaa_csvs'
PROVINCE_CSV_DIR = DOWNLOADS_DIR / 'carlos_iii_province_csvs'

MINISTRY_REPORTS_TO_SKIP = ['Actualizacion_137_COVID-19']
CACHE_DIR = BASE_DIR / 'caches'
