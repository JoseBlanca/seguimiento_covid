
import config

import requests

MINISTRY_REPORT_BASE_URL = 'https://www.mscbs.gob.es/profesionales/saludPublica/ccayes/alertasActual/nCov/documentos/Actualizacion_{}_COVID-19.pdf'


def download_ministry_reports():
    for idx in range(31, 10000):
        url = MINISTRY_REPORT_BASE_URL.format(idx)
        fname = url.split('/')[-1]
        out_path = config.MINISTRY_REPORTS_DIR / fname
        if out_path.exists():
            continue

        response = requests.get(url)

        if response.status_code == 404:
            break

        with out_path.open('wb') as fhand:
            for chunk in response.iter_content(chunk_size=128):
                fhand.write(chunk)


if __name__ == '__main__':
    download_ministry_reports()