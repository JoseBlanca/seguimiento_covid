
import config

import datetime

import data_sources
from generate_report import write_html_report


def write_html_report_for_spa(date_range):
    out_dir = config.HTML_REPORTS_DIR
    out_dir.mkdir(exist_ok=True)
    out_path = out_dir / f'situacion_covid_spa.html'
    write_html_report(out_path, spa_report=True, date_range=date_range)


if __name__ == '__main__':

    ten_days_ago = datetime.datetime.now() - datetime.timedelta(days=10)
    forty_days_ago = datetime.datetime.now() - datetime.timedelta(days=40)
    first_date = datetime.datetime(2020, 9, 1)

    write_html_report_for_spa(date_range=[forty_days_ago, ten_days_ago])

