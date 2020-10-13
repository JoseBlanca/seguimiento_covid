
import config

import os
import datetime

import requests

MINISTRY_REPORT_BASE_URL = 'https://www.mscbs.gob.es/profesionales/saludPublica/ccayes/alertasActual/nCov/documentos/Actualizacion_{}_COVID-19.pdf'
MINISTRY_DECEASED_EXCEL_URL = 'https://www.mscbs.gob.es/profesionales/saludPublica/ccayes/alertasActual/nCov-China/documentos/Fallecidos_COVID19.xlsx'
CARLOS_III_CCAA_DATA_URL = 'https://cnecovid.isciii.es/covid19/resources/datos_ccaas.csv'
CARLOS_III_PROVICE_DATA_URL = 'https://cnecovid.isciii.es/covid19/resources/datos_provincias.csv'


def mkdir(directory):
    os.makedirs(directory, exist_ok=True)


def download_ministry_reports():
    out_dir = config.MINISTRY_REPORTS_DIR
    mkdir(out_dir)
    for idx in range(31, 10000):
        url = MINISTRY_REPORT_BASE_URL.format(idx)
        fname = url.split('/')[-1]
        out_path = out_dir / fname
        if out_path.exists():
            continue

        response = requests.get(url)

        if response.status_code == 404:
            break

        with out_path.open('wb') as fhand:
            for chunk in response.iter_content(chunk_size=128):
                fhand.write(chunk)


def download_daily_file(url, out_dir):
    mkdir(out_dir)
    fname = url.split('/')[-1]
    base_name, extension = fname.split('.')
    today = datetime.datetime.now().date()
    out_fname = f'{base_name}.{today.year}-{today.month}-{today.day}.{extension}'
    out_path = out_dir / out_fname
    if out_path.exists():
        return

    response = requests.get(url)
    if response.status_code == 404:
        raise RuntimeError(f'Error downloading url: {url}')

    with out_path.open('wb') as fhand:
        for chunk in response.iter_content(chunk_size=128):
            fhand.write(chunk)


def download_deceased_ministry_excel():
    download_daily_file(MINISTRY_DECEASED_EXCEL_URL,
                        config.DECEASED_EXCEL_DIR)


def download_ccaa_carlos_iii_csv():
    download_daily_file(CARLOS_III_CCAA_DATA_URL,
                        config.CCAA_CSV_DIR)


def download_provices_carlos_iii_csv():
    download_daily_file(CARLOS_III_PROVICE_DATA_URL,
                        config.PROVINCE_CSV_DIR)

if __name__ == '__main__':
    download_ministry_reports()
    download_deceased_ministry_excel()
    download_ccaa_carlos_iii_csv()
    download_provices_carlos_iii_csv()
