
from pathlib import Path

BASE_DIR = Path('/home/jose/devel/covid_situation/')
DATADISTA_DIR = BASE_DIR / 'timestamped_datasets'
DATADISTA_TIMESTAMPS_TO_EXCLUDE = [1591817222]
DOWNLOADED_DATASETS_DIR = BASE_DIR / 'downloaded_datasets'

PLOT_DIR = BASE_DIR / 'plots'

MINISTRY_REPORTS_DIR = BASE_DIR / 'informes_ministerio'

MINISTRY_REPORTS_TO_SKIP = ['Actualizacion_137_COVID-19']
CACHE_DIR = BASE_DIR / 'caches'
