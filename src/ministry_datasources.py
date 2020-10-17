
from ast import parse
from functools import partial

import config

import datetime
import pickle, gzip

import numpy
import pandas

import xlrd

from pdfminer import high_level
import tabula

import data_sources

COL_NAMES = ['hospitalizacion_total', 'hospitalizacion_7_dias',
             'uci_total', 'uci_7_dias',
             'fallecidos_total', 'fallecidos_7_dias'
            ]


def _extract_text(text, start, end=None):

    start = text.find(start) + len(start)
    if end is not None:
        end = text[start:].find(end) + start

    extracted_text = text[start: end]
    return extracted_text


def _extract_column(text, start, end):
    text = _extract_text(text, start, end)
    column = []
    for item in text.split('\n'):
        item = item.strip()
        if not item and not column:
            continue
        column.append(item)

    if not column[-1]:
        column = column[:-1]
    return column


def _extract_number_columns(text, start_text, end_text=None):
    items = _extract_text(text, start_text, end_text).split('\n')
    column = []
    columns = []
    for item in items:
        item = item.replace('.', ',').replace(',', '').strip()
        if item.isdigit():
            num = int(item)
            column.append(num)
        else:
            if column:
                columns.append(column[:])
                column = []
    return columns


def _get_some_partial_sorted_columns(pdf_path, text):

    int_converter = lambda x: int(x.replace('.', '').replace(',', '') if '.' in x or ',' in x else int(x))
    converters = {idx: int_converter for idx in range(1, 10)}
    pandas_options = {'converters': converters, 'header':None, 'index_col': 0}

    if 'Tabla 3. PCR procesadas' in text:
        left = 70
        width = 600
        height = 300
        top = 210
    elif 'Página 2 de 11' in text:
        if '** Se está' in text:
            left = 70
            width = 730
            height = 300
            top = 210
        else:
            left = 70
            width = 730
            height = 380
            top = 200
    elif '*' not in text and 'Los casos confirmados no provienen de la suma de pacientes hospitalizados, curados y fallecidos, ya que ' in text:
            left = 70
            width = 730
            height = 380
            top = 200
    elif 'Tabla 2. Casos de COVID-19 que' in text:
        left = 70
        width = 730
        height = 300
        top = 210

    table = tabula.read_pdf(pdf_path, pages=[2], area=(top, left, height, width),
                            output_format='dataframe', multiple_tables=False,
                            pandas_options=pandas_options)[0]
    columns = [list(table.iloc[:, idx].values) for idx in range(0, 6)]
    return columns


def _sublist_is_in_list(sublist, list):
    try:
        first_idx = list.index(sublist[0])
    except ValueError:
        return False

    for idx in range(first_idx, len(list) - len(sublist) + 1):
        if all(item == list[idx + idx2]  for idx2, item in enumerate(sublist)):
            return True
    return False


def _key(column, partial_sorted_columns):
    for idx in range(6):
        if _sublist_is_in_list(partial_sorted_columns[idx], column):
            return idx
    raise ValueError('no partial column matches the given column')


def _sort_columns(columns, partial_sorted_columns):
    key = partial(_key, partial_sorted_columns=partial_sorted_columns)
    columns = sorted(columns, key=key)
    return columns
    

class EmptyRowError(RuntimeError):
    pass


def _parse_report_1(pdf_path):
    print(pdf_path)
    text = high_level.extract_text(pdf_path.open('rb'), page_numbers=[0])
    date_start = text.find('horas del') + 10
    date = text[date_start: date_start + 10]
    day, month, year = map(int, date.split('.'))
    date = datetime.datetime(year=year, month=month, day=day)

    text = high_level.extract_text(pdf_path.open('rb'), page_numbers=[1])
    ccaas = _extract_column(text, 'CCAA', 'ESPA')

    if not ccaas[ccaas.index('Extremadura') + 1]:
        raise EmptyRowError('Report with empty_row: ' + str(pdf_path))
    assert all(ccaas)
    assert ccaas[0] == 'Andalucía'
    assert ccaas[-1] == 'La Rioja'

    if 'Tabla 3. PCR procesadas' in text:
        columns = _extract_number_columns(text, 'ESPA', 'CCAA')
    else:
        columns = _extract_number_columns(text, 'ESPA')
    columns = [column for column in columns if len(column) > 17]

    partial_sorted_columns = _get_some_partial_sorted_columns(pdf_path, text)

    columns = _sort_columns(columns, partial_sorted_columns)

    if len(columns[0]) == len(ccaas) + 1:
        columns = [column[:-1] for column in columns]

    assert all(len(column) == len(ccaas) for column in columns)

    table = pandas.DataFrame(dict(zip(COL_NAMES, columns)), index=ccaas)
    return {'date': date, 'hospitalizacion_y_fallecidos': table}


def _parse_report_2(pdf_path, left, width, top, height, debug=False):
    print(pdf_path)
    text = high_level.extract_text(pdf_path.open('rb'), page_numbers=[0])
    date_start = text.find('horas del') + 10
    date = text[date_start: date_start + 10]
    day, month, year = map(int, date.split('.'))
    date = datetime.datetime(year=year, month=month, day=day)


    int_converter = lambda x: int(x.replace('.', '').replace(',', '') if '.' in x or ',' in x else int(x))
    converters = {idx: int_converter for idx in range(1, 10)}
    pandas_options = {'converters': converters, 'header':None, 'index_col': 0}

    table = tabula.read_pdf(pdf_path, pages=[2], area=(top, left, height, width),
                            output_format='dataframe', multiple_tables=False,
                            pandas_options=pandas_options)[0]
    # print(table)
    if list(table.index)[-1].startswith('ESPA'):
        table = table.reindex(list(table.index)[:-1])

    table.columns = COL_NAMES
    return {'date': date, 'hospitalizacion_y_fallecidos': table}


def parse_report(path):

    cache_path = config.CACHE_DIR / (str(path.stem) + '.pickle.gz')

    if cache_path.exists():
        report = pickle.load(gzip.open(cache_path, 'rb'))
        new_report = False
    else:
        report_num = int(path.stem.split('_')[1])
        if report_num >= 226:
            left = 80
            width = 810
            height = 450
            top = 180
            report = _parse_report_2(path, left, width, top, height)
        elif report_num in [168, 169, 174, 177, 178, 179, 180]:
            left = 80
            width = 810
            height = 430
            top = 190
            report = _parse_report_2(path, left, width, top, height)
        elif report_num in [176]:
            left = 80
            width = 810
            height = 440
            top = 190
            report = _parse_report_2(path, left, width, top, height)
        elif report_num >=206 and report_num <= 208:
            left = 80
            width = 810
            height = 460
            top = 190
            report = _parse_report_2(path, left, width, top, height)
        elif report_num >=209 and report_num <= 219:
            left = 80
            width = 810
            height = 460
            top = 180
            report = _parse_report_2(path, left, width, top, height)
        elif report_num >=220 and report_num <= 223:
            left = 80
            width = 810
            height = 460
            top = 190
            report = _parse_report_2(path, left, width, top, height)
        elif report_num >=224 and report_num <= 225:
            left = 80
            width = 810
            height = 460
            top = 180
            report = _parse_report_2(path, left, width, top, height)
        elif report_num < 189 or report_num >= 206:
            report = _parse_report_1(path)
        else:
            left = 70
            width = 830
            height = 450
            top = 170
            report = _parse_report_2(path, left, width, top, height)
        new_report = True
    
    dframe = report['hospitalizacion_y_fallecidos']

    if dframe.isnull().values.any():
        msg = f'Empty values in {path}'
        raise RuntimeError(msg)
    assert len(dframe.columns) == 6
    ccaas = list(dframe.index)
    assert ccaas[0] == 'Andalucía'
    assert ccaas[-1] == 'La Rioja'

    dframe.index = [ccaa.strip('*') for ccaa in dframe.index]

    if new_report:
        pickle.dump(report, gzip.open(cache_path, 'wb'))

    return report


def get_ministry_cum_data(report_paths, skip_reports_with_empty_rows=False):

    hospitalized = {}
    icu = {}
    deceased = {}
    index = None
    for path in report_paths:
        try:
            result = parse_report(path)
        except EmptyRowError:
            if skip_reports_with_empty_rows:
                continue
            else:
                raise
        
        hospitalized[result['date']] = result['hospitalizacion_y_fallecidos']['hospitalizacion_total']
        icu[result['date']] = result['hospitalizacion_y_fallecidos']['uci_total']
        deceased[result['date']] = result['hospitalizacion_y_fallecidos']['fallecidos_total']

        if index is None:
            index = list(result['hospitalizacion_y_fallecidos'].index)
        else:
            #print(index)
            #print(result['hospitalizacion_y_fallecidos'].index)
            assert index == list(result['hospitalizacion_y_fallecidos'].index)

    hospitalized = pandas.DataFrame(hospitalized, index=index)
    icu = pandas.DataFrame(icu, index=index)
    deceased = pandas.DataFrame(deceased, index=index)
    assert not hospitalized.isnull().values.any()
    assert not icu.isnull().values.any()
    assert not deceased.isnull().values.any()
    result = {'hospitalized': hospitalized, 'icu': icu, 'deceased': deceased}

    return result


def get_ministry_valid_reports():
    paths = []
    for path in config.MINISTRY_REPORTS_DIR.iterdir():
        if 'pdf' not in str(path):
            continue
        if path.stem in config.MINISTRY_REPORTS_TO_SKIP:
            continue
        report_num = int(path.stem.split('_')[1])
        if report_num < 116:
            continue
        paths.append(path)
    return sorted(paths)


def _get_next_date(date, dates_with_increments, last_date_with_incr):
    if date in dates_with_increments:
        last_date_with_incr = date
        return date, last_date_with_incr

    return dates_with_increments[dates_with_increments.index(last_date_with_incr) + 1], last_date_with_incr


def get_incremental_table_from_cum_table(cum_table):
    cum_table = cum_table.reindex(columns=sorted(cum_table.columns))

    dates = numpy.array(cum_table.columns)
    num_days_increments = (dates[1:] - dates[:-1]) / numpy.timedelta64(1, 'D')
    increments = (cum_table.iloc[:, 1:].values - cum_table.iloc[:, :-1].values) / num_days_increments
    increments = pandas.DataFrame(increments, columns=dates[1:])

    incr_dates = pandas.date_range(start=dates[1], end=dates[-1])
    dates_with_increments = list(increments.columns)
    last_date_with_incr = None
    one_day_increments = {}
    for date in incr_dates:
        next_date_with_incr, last_date_with_incr = _get_next_date(date, dates_with_increments, last_date_with_incr)
        incr_for_this_date = increments.loc[:, next_date_with_incr]
        one_day_increments[date] = incr_for_this_date.values

    one_day_increments = pandas.DataFrame(one_day_increments, index=cum_table.index, columns=incr_dates)

    return one_day_increments


def get_ministry_incremental_data(skip_reports_with_empty_rows=False):
    report_paths = get_ministry_valid_reports()
    cum_data = get_ministry_cum_data(report_paths, skip_reports_with_empty_rows=False)
    incr_data = {key: get_incremental_table_from_cum_table(this_cum_data) for key, this_cum_data in cum_data.items()}
    return incr_data


def get_ministry_rolling_mean(num_days=7):

    incr_data = get_ministry_incremental_data()

    rolling_means = {}
    for key, this_incr_data in incr_data.items():
        rolling_mean = this_incr_data.rolling(num_days, center=True, min_periods=num_days, axis=1).mean()
        rolling_mean = rolling_mean.dropna(axis=1, how='all')
        assert not rolling_mean.isnull().values.any()
        rolling_means[key] = rolling_mean
    return rolling_means


def _read_deaths_to_assing(path):
    sheet = xlrd.open_workbook(path).sheet_by_index(0)
    text = str(sheet.cell(sheet.nrows - 1, 0))
    if not 'fecha de defunción en' in text:
        raise RuntimeError('Unknown unassinged deaths format')
    return int(text[text.index('fecha de defunción en') + 22:].split()[0])


def read_deceased_excel_ministry_files():
    for path in config.DECEASED_EXCEL_DIR.iterdir():
        if not str(path).endswith('.xlsx'):
            continue
        dframe = pandas.read_excel(path, index_col=0, parse_dates=True, skipfooter=1).T
        dframe = dframe.reindex(list(dframe.index)[:-1])
        last_date = dframe.columns[-1]
        unassinged_deaths = _read_deaths_to_assing(path)
        yield {'dframe': dframe, 'max_date': last_date, 'unassinged_deaths': unassinged_deaths}


def get_sorted_deceased_excel_ministry_files(filter_out_reports_with_same_max_date=True):
    reports = read_deceased_excel_ministry_files()
    return data_sources._get_sorted_reports(reports, filter_out_reports_with_same_max_date)


if __name__ == '__main__':

    print(get_sorted_deceased_excel_ministry_files())

    assert False
    #report_paths = get_ministry_valid_reports()
    #cum_data = get_ministry_cum_data(report_paths[-2:])
    #result = parse_report(config.MINISTRY_REPORTS_DIR/ 'Actualizacion_213_COVID-19.pdf')
    #print(result['hospitalizacion_y_fallecidos'])
    #result = parse_report(config.MINISTRY_REPORTS_DIR/ 'Actualizacion_214_COVID-19.pdf')
    #print(result['hospitalizacion_y_fallecidos'])
    report_paths = get_ministry_valid_reports()
    cum_data = get_ministry_cum_data(report_paths, skip_reports_with_empty_rows=False)
    print(cum_data.keys())
    incr_data = get_incremental_table_from_cum_table(cum_data['deceased'])
    print(incr_data)

    get_ministry_rolling_mean(num_days=7)
