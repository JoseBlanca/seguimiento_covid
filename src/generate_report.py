
from datetime import date
import config

import datetime

import numpy
import pandas

import data_sources
from data_sources import POPULATION
import material_line_chart
import ministry_datasources


HEADER1 = '''<html>
  <head>
    <script type="text/javascript" src="https://www.gstatic.com/charts/loader.js"></script>
    <script type="text/javascript">
      google.charts.load('current', {'packages':['line']});

'''

DESCRIPTIONS = {
'incidencia_acumulada': 'Número de casos detectados en los 15 días anteriores por cien mil habitantes. Datos obtenidos de los informes del Carlos III.',
'hospitalized': 'Número medio de hospitalizaciones por cien mil habitantes (media de 7 días). Datos obtenidos a partir de las cifras acumuladas que aparecen en los informes diarios del ministerio.',
'deceased': 'Número medio de fallecidos por cien mil habitantes (media de 7 días). Datos obtenidos a partir de las cifras acumuladas que aparecen en los informes diarios del ministerio.',
}


def calc_accumulated_indicende_per_ccaa(report, num_days=15):
    ccaas = data_sources.get_ccaas_in_dset(report)
    dframe = report['dframe']
    num_cases = dframe['num_casos']    
    ccaa_column = data_sources.get_ccaa_column_in_index(num_cases.index)
    index = num_cases.index.to_frame(index=False)

    dates = index['fecha']
    time_delta = numpy.timedelta64(num_days, 'D')

    accumulated_cases_by_ccaa = {}
    for ccaa in ccaas:
        mask = index[ccaa_column] == ccaa
        mask = mask.values
        num_cases_for_this_ccaa = num_cases[mask]
        this_ccaa_index = num_cases_for_this_ccaa.index.to_frame(index=False)
        this_ccaa_dates = this_ccaa_index['fecha']
        num_accumulated_cases = []
        valid_dates = []
        for date in this_ccaa_dates:
            date0 = date - time_delta
            mask = numpy.logical_and(this_ccaa_dates > date0,
                                     this_ccaa_dates <= date)
            mask = mask.values
            if numpy.sum(mask) < num_days:
                continue
            num_accumulated_cases.append(numpy.sum(num_cases_for_this_ccaa[mask]))
            valid_dates.append(date)
            
        num_accumulated_cases = pandas.Series(num_accumulated_cases, index=valid_dates)
        num_accumulated_cases = num_accumulated_cases / data_sources.POPULATION[ccaa] * 1e5
        accumulated_cases_by_ccaa[ccaa] = num_accumulated_cases
    return accumulated_cases_by_ccaa


def _create_js_chart(dframe, date_range, js_function_name, div_id, title, width, height):
    table = []
    ccaas = sorted(dframe.index)
    dates = list(dframe.columns)

    if date_range is not None:
        dates = [date for date in dates if date > date_range[0] and date <= date_range[1]]

    columns = [('date', 'fecha')]
    columns.extend([('number', data_sources.convert_to_ccaa_name(ccaa)) for ccaa in ccaas])

    for date in dates:
        row = [date.date()]
        for ccaa in ccaas:
            value = dframe.loc[ccaa, date]
            row.append(value)
        table.append(row)
    js_function_name = js_function_name
    html = material_line_chart.create_chart_js(js_function_name, div_id, title,
                                               columns, table,
                                               width=width, height=height)
    return html


def _write_table_from_series(series):
    html = '<table>'
    for index, value in zip(series.index, series.values):
        html += f'<tr><td>{index}</td><td>{value}</td></tr>\n'
    html += '</table>'
    return html


def write_html_report(fname, date_range=None):

    ccaa_info = data_sources.get_sorted_downloaded_ccaa_info()
    report = ccaa_info[-1]
    accumulaed_incidence = calc_accumulated_indicende_per_ccaa(report)

    deaths = sorted(ministry_datasources.read_deceased_excel_ministry_files(),
                    key=lambda x: x['last_date'])[-1]

    #deaths_dframe = deaths['dframe']

    one_accumulated_incidence = list(accumulaed_incidence.values())[0]

    ccaas = sorted(accumulaed_incidence.keys())
    dates = list(one_accumulated_incidence.index)
    if date_range is not None:
        dates = [date for date in dates if date > date_range[0] and date <= date_range[1]]

    accumulated_incidence_table = []
    for date in dates:
        row = [date.date()]
        for ccaa in ccaas:
            row.append(accumulaed_incidence[ccaa][date])
        accumulated_incidence_table.append(row)

    out_path = config.PLOT_DIR / fname
    html = HEADER1

    js_function_name = 'drawAccumulatedCasesIncidence'
    div_id_accumulated_cases = 'accumulated_cases_chart'
    width = 900
    height = 750
    columns = [('date', 'fecha')]
    columns.extend([('number', data_sources.convert_to_ccaa_name(ccaa)) for ccaa in ccaas])
    title = 'Indicencia acumulada por 100.000 hab. (15 días)'
    html += material_line_chart.create_chart_js(js_function_name, div_id_accumulated_cases, title,
                                                columns, accumulated_incidence_table,
                                                width=width, height=height)

    js_function_names = {'hospitalized': 'drawHospitalized',
                         'icu': 'drawICU',
                         'deceased': 'drawDeceased'}
    div_ids = {'hospitalized': 'hospitalized_chart',
               'icu': 'icu_chart',
               'deceased': 'deceased_chart'
              }
    titles = {'hospitalized': 'Num. hospitalizaciones por 100.000 hab. (media 7 días)',
              'icu': 'Num. ingresos UCI por 100.000 hab. (media 7 días)',
              'deceased': 'Num. fallecidos por 100.000 hab. (media 7 días)'
              }

    rolling_means = ministry_datasources.get_ministry_rolling_mean()

    used_rolling_means = ['hospitalized', 'deceased']

    for key in used_rolling_means:
        dframe = rolling_means[key]
        populations = [data_sources.get_population(ccaa) for ccaa in dframe.index]
        dframe = dframe.divide(populations, axis=0) * 1e5
        html += _create_js_chart(dframe, date_range=date_range,
                                 js_function_name=js_function_names[key],
                                 div_id=div_ids[key],
                                 title=titles[key],
                                 width=width,
                                 height=height)

    html += '    </script>\n  </head>\n  <body>\n'

    today = datetime.datetime.now()
    html += f'<p>Informe generado el día: {today.day}-{today.month}-{today.year}</p>'

    tot_deaths = deaths['dframe'].values.sum() + deaths['unassinged_deaths']
    html += f'<p>Número total de fallecidos: {tot_deaths}</p>'

    deaths_per_ccaa = deaths['dframe'].sum(axis=1)
    populations = [data_sources.get_population(ccaa) for ccaa in deaths_per_ccaa.index]
    populations = pandas.Series(populations, index=deaths_per_ccaa.index)
    death_rate = (populations / deaths_per_ccaa).round().sort_values().astype(int)
    html += '<p>¿Una de cada cuántas personas han fallecido por comunidad autónoma?</p>'
    html += _write_table_from_series(death_rate)

    html += f"<p>{DESCRIPTIONS['incidencia_acumulada']}</p>\n"
    html += f'<div id="{div_id_accumulated_cases}" style="width: {width}px; height: {height}px"></div>\n'

    for key in used_rolling_means:
        html += f"<p>{DESCRIPTIONS[key]}</p>\n"
        div_id = div_ids[key]
        html += f'<div id="{div_id}" style="width: {width}px; height: {height}px"></div>\n'

    html += '  </body>\n</html>'

    out_path.open('wt').write(html)


if __name__ == '__main__':

    ten_days_ago = datetime.datetime.now() - datetime.timedelta(days=10)
    forty_days_ago = datetime.datetime.now() - datetime.timedelta(days=40)
    first_date = datetime.datetime(2020, 9, 1)

    write_html_report('situacion_covid_por_ca_ultimo_mes.html', date_range=[forty_days_ago, ten_days_ago])
    write_html_report('situacion_covid_por_ca.html')

