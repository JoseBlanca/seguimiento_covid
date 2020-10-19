
from datetime import date
import config

import datetime

import numpy
import pandas

import data_sources
from data_sources import POPULATION, convert_to_ccaa_iso
import material_line_chart
import ministry_datasources


HEADER = '''<html>
  <head>
    <title>{}</title>
    <script type="text/javascript" src="https://www.gstatic.com/charts/loader.js"></script>
    <script type="text/javascript">
'''

HEADER2 = '''
      google.charts.load('current', {'packages':['line', 'corechart', 'controls']});

'''


DESCRIPTIONS_CCAA = {
'incidencia_acumulada': 'Número de casos informados en los 15 días anteriores por cien mil habitantes. Datos obtenidos de los informes del Carlos III.',
'hospitalized': 'Número medio de hospitalizaciones por cien mil habitantes (media de 7 días). Datos obtenidos a partir de las cifras acumuladas que aparecen en los informes diarios del ministerio.',
'deceased': 'Número medio de fallecidos por cien mil habitantes (media de 7 días). Datos obtenidos a partir del excel con datos de fallecidos diarios del ministerio.',
}
DESCRIPTIONS_SPA = {
'incidencia_acumulada': 'Número de casos informados en los 15 días anteriores por cien mil habitantes. Datos obtenidos de los informes del Carlos III.',
'hospitalized': 'Número medio de hospitalizaciones (media de 7 días). Datos obtenidos a partir de las cifras acumuladas que aparecen en los informes diarios del ministerio.',
'deceased': 'Número medio de fallecidos (media de 7 días). Datos obtenidos a partir del excel con datos de fallecidos diarios del ministerio.',
}
DESCRIPTIONS = {True: DESCRIPTIONS_SPA, False: DESCRIPTIONS_CCAA}


def calc_accumulated_indicende_per_ccaa(report, num_days=15):
    ccaas = data_sources.get_ccaas_in_dset(report)
    dframe = report['dframe']
    num_cases = dframe['num_casos']    
    ccaa_column = data_sources.get_ccaa_column_in_index(num_cases.index)
    index = num_cases.index.to_frame(index=False)

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


def is_desired_ccaa(ccaa, desired_ccaas):
    return desired_ccaas is None or data_sources.convert_to_ccaa_iso(ccaa) in desired_ccaas


def _create_table_for_chart_from_dict(dict_data, desired_ccaas):
    one_data = list(dict_data.values())[0]

    ccaas = sorted(dict_data.keys())
    ccaas = [ccaa for ccaa in ccaas if is_desired_ccaa(ccaa, desired_ccaas)]

    dates = list(one_data.index)
    table = []
    for date in dates:
        row = [date.date()]
        for ccaa in ccaas:
            row.append(dict_data[ccaa][date])
        table.append(row)
    return table, ccaas, dates


def _create_accumulate_indicence_table_for_spa_chart_from_report(report, num_days):
    dframe = report['dframe']
    time_delta = numpy.timedelta64(num_days, 'D')

    num_cases = dframe.groupby(level=1).sum().loc[:, 'num_casos']

    tot_pop = sum(data_sources.POPULATION.values())
    dates = numpy.array(num_cases.index)
    num_accumulated_cases = []
    valid_dates = []
    for date in dates:
        date0 = date - time_delta
        mask = numpy.logical_and(dates > date0,
                                 dates <= date)
        if numpy.sum(mask) < num_days:
            continue
        num_accumulated_cases.append(numpy.sum(num_cases[mask]) / tot_pop * 1e5)
        date = datetime.datetime.fromtimestamp(date.astype('O') / 1e9)
        valid_dates.append(date)

    table = [(date.date(), cases) for date, cases in zip(valid_dates, num_accumulated_cases)]
    dates = valid_dates

    return table, dates


def _create_table_for_chart_from_dframe(dframe, desired_ccaas):

    ccaas = sorted(dframe.index)
    ccaas = [ccaa for ccaa in ccaas if is_desired_ccaa(ccaa, desired_ccaas)]
    dates = list(dframe.columns)
    table = []
    for date in dates:
        row = [date.date()]
        for ccaa in ccaas:
            row.append(dframe.loc[ccaa, date])
        table.append(row)
    return table, ccaas, dates


def _create_table_for_chart_from_series(series):
    table = [(date.date(), value) for date, value in zip(series.index, series.values)]
    return table


def write_html_report(out_path, date_range=None, desired_ccaas=None, spa_report=False):

    if spa_report and desired_ccaas:
        raise ValueError('choose one, either spa or ccaa report')

    if desired_ccaas and len(desired_ccaas) == 1:
        only_one_ccaa = True
        ccaa_iso = convert_to_ccaa_iso(desired_ccaas[0])
    else:
        only_one_ccaa = False

    ccaa_info = data_sources.get_sorted_downloaded_ccaa_info()
    report = ccaa_info[-1]
    accumulaed_incidence = calc_accumulated_indicende_per_ccaa(report)

    deaths = sorted(ministry_datasources.read_deceased_excel_ministry_files(),
                    key=lambda x: x['max_date'])[-1]

    if spa_report:
        accumulated_incidence_table, dates = _create_accumulate_indicence_table_for_spa_chart_from_report(report, 15)
    else:
        accumulated_incidence_table, ccaas, dates = _create_table_for_chart_from_dict(accumulaed_incidence, desired_ccaas)

    title = 'Resumen situación Covid-19'
    if spa_report:
        title += ' España'
    elif only_one_ccaa:
        title += ': ' + data_sources.convert_to_ccaa_name(ccaa_iso)
    else:
        title += ' por comunidad autónoma'
    html = HEADER.format(title)
    html += HEADER2

    js_function_name = 'drawAccumulatedCasesIncidence'
    columns = [('date', 'fecha')]
    if spa_report:
        columns.extend([('number', 'España')])
    else:
        columns.extend([('number', data_sources.convert_to_ccaa_name(ccaa)) for ccaa in ccaas if is_desired_ccaa(ccaa, desired_ccaas)])
    title = 'Indicencia acumulada por 100.000 hab. (15 días)'

    width =900
    height = 800
    rangeslider_height = 50
    js_sizes = {'dashboard': {'height': height + rangeslider_height, 'width': width},
                'chart': {'height': height, 'width': width},
                'rangeslider': {'height': rangeslider_height, 'width': 600},
               }
    div_sizes = {}
    for html_element in js_sizes:
        div_sizes[html_element] = {}
        div_sizes[html_element]['height'] = f"{js_sizes[html_element]['height']}px"
        div_sizes[html_element]['width'] = f"{js_sizes[html_element]['width']}px"

    slider_config = {'column_controlled': 'fecha',
                     'min_value': dates[0],
                     'max_value': dates[-1],
                     'min_init_value': date_range[0],
                     'max_init_value': date_range[-1]}
    div_ids_accumulated_cases = {'dashboard': 'accumulated_cases_dashboard',
                                 'chart': 'accumulated_cases_chart',
                                 'rangeslider': 'accumulated_cases_rangeslider'}

    html += material_line_chart.create_chart_js_with_slider(js_function_name,
                                                            slider_config,
                                                            div_ids_accumulated_cases,
                                                            title,
                                                            columns,
                                                            accumulated_incidence_table,
                                                            sizes=js_sizes)

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

    if spa_report:
        rolling_means = ministry_datasources.get_ministry_rolling_mean_spa()
        titles = {'hospitalized': 'Num. hospitalizaciones. (media 7 días)',
                  'icu': 'Num. ingresos UCI. (media 7 días)',
                  'deceased': 'Num. fallecidos. (media 7 días)'
                  }
    else:
        rolling_means = ministry_datasources.get_ministry_rolling_mean()
        titles = {'hospitalized': 'Num. hospitalizaciones por 100.000 hab. (media 7 días)',
                  'icu': 'Num. ingresos UCI por 100.000 hab. (media 7 días)',
                  'deceased': 'Num. fallecidos por 100.000 hab. (media 7 días)'
                  }


    div_ids_hospitalized = {'dashboard': 'hospitalized_dashboard',
                            'chart': 'hospitalized_chart',
                            'rangeslider': 'hospitalized_rangeslider'}
    div_ids_deceased = {'dashboard': 'deceased_dashboard',
                        'chart': 'deceased_chart',
                        'rangeslider': 'deceased_rangeslider'}
    div_ids = {'hospitalized': div_ids_hospitalized,
               'deceased': div_ids_deceased,
              }

    dframe = rolling_means['hospitalized']
    if spa_report:
        columns = [('date', 'fecha'), ('number', 'España')]
        table = _create_table_for_chart_from_series(dframe)
    else:
        populations = [data_sources.get_population(ccaa) for ccaa in dframe.index]
        dframe = dframe.divide(populations, axis=0) * 1e5
        table, ccaas, _ = _create_table_for_chart_from_dframe(dframe, desired_ccaas)
        columns = [('date', 'fecha')]
        columns.extend([('number', data_sources.convert_to_ccaa_name(ccaa)) for ccaa in ccaas])

    key = 'hospitalized'
    hospitalized_slider_config = {'column_controlled': 'fecha',
                                   'min_value': dates[0],
                                   'max_value': dates[-1],
                                   'min_init_value': date_range[0],
                                   'max_init_value': datetime.datetime.now()}
    html += material_line_chart.create_chart_js_with_slider(js_function_names[key],
                                                            hospitalized_slider_config,
                                                            div_ids[key],
                                                            title=titles[key],
                                                            columns=columns,
                                                            data_table=table,
                                                            sizes=js_sizes)

    num_days = 7
    key = 'deceased'
    deaths_dframe = deaths['dframe']
    if spa_report:
        spa_deaths = deaths_dframe.sum(axis=0)
        deaths_rolling_mean = spa_deaths.rolling(num_days, center=True, min_periods=num_days).mean().dropna()
        table = _create_table_for_chart_from_series(deaths_rolling_mean)
        columns = [('date', 'fecha'), ('number', 'España')]
    else:
        deaths_rolling_mean = deaths_dframe.rolling(num_days, center=True, min_periods=num_days, axis=1).mean()
        deaths_rolling_mean = deaths_rolling_mean.dropna(axis=1, how='all')
        populations = [data_sources.get_population(ccaa) for ccaa in deaths_rolling_mean.index]
        deaths_rolling_mean = deaths_rolling_mean.divide(populations, axis=0) * 1e5

        table, ccaas, _ = _create_table_for_chart_from_dframe(deaths_rolling_mean, desired_ccaas)
        columns = [('date', 'fecha')]
        columns.extend([('number', data_sources.convert_to_ccaa_name(ccaa)) for ccaa in ccaas])

    html += material_line_chart.create_chart_js_with_slider(js_function_names[key],
                                                            slider_config,
                                                            div_ids[key],
                                                            title=titles[key],
                                                            columns=columns,
                                                            data_table=table,
                                                            sizes=js_sizes)

    html += '    </script>\n  </head>\n  <body>\n'
    today = datetime.datetime.now()
    html += '<p><a href="../">Menu</a></p>'
    html += f'<p>Informe generado el día: {today.day}-{today.month}-{today.year}</p>'

    html += f'<p>Este informe está generado para uso personal por <a href="https://twitter.com/jblanca42">@jblanca42</a>, pero lo sube a la web por si le pudiese ser de utilidad a alguien más.</p>'
    html += f'<p>El código utilizado para generarlo se encuentra en <a href="https://github.com/JoseBlanca/seguimiento_covid">github</a>, si encuentras algún fallo o quieres mejorar algo envía un mensaje o haz un pull request.</p>'

    if desired_ccaas:
        index = [ccaa for ccaa in deaths['dframe'].index if is_desired_ccaa(ccaa, desired_ccaas)]
        tot_deaths = deaths['dframe'].loc[index, :].values.sum()
    else:
        tot_deaths = deaths['dframe'].values.sum() + deaths['unassinged_deaths']
    html += f'<p>Número total de fallecidos: {tot_deaths}</p>'

    if spa_report:
        death_rate = round(sum(data_sources.POPULATION.values()) / tot_deaths)
        html += f'<p>Una de cada {death_rate} personas han fallecido.</p>'
    elif desired_ccaas and len(desired_ccaas) == 1:
        death_rate = round(data_sources.get_population(desired_ccaas[0]) / tot_deaths)
        html += f'<p>Una de cada {death_rate} personas han fallecido en esta comunidad autónoma.</p>'
    else:
        deaths_per_ccaa = deaths['dframe'].sum(axis=1)
        populations = [data_sources.get_population(ccaa) for ccaa in deaths_per_ccaa.index]
        populations = pandas.Series(populations, index=deaths_per_ccaa.index)
        death_rate = (populations / deaths_per_ccaa).round().sort_values().astype(int)
        html += '<p>¿Una de cada cuántas personas han fallecido por comunidad autónoma?</p>'
        html += _write_table_from_series(death_rate)

    for key in ['hospitalized']:
        html += f"<p>{DESCRIPTIONS[spa_report][key]}</p>\n"
        html += material_line_chart.create_chart_with_slider_divs(div_ids[key],
                                                                  sizes=div_sizes)

    html += f"<p>{DESCRIPTIONS[spa_report]['incidencia_acumulada']}</p>\n"

    html += material_line_chart.create_chart_with_slider_divs(div_ids_accumulated_cases,
                                                              sizes=div_sizes)
    for key in ['deceased']:
        html += f"<p>{DESCRIPTIONS[spa_report][key]}</p>\n"
        html += material_line_chart.create_chart_with_slider_divs(div_ids[key],
                                                                  sizes=div_sizes)

    html += '  </body>\n</html>'

    out_path.open('wt').write(html)


if __name__ == '__main__':

    ten_days_ago = datetime.datetime.now() - datetime.timedelta(days=10)
    forty_days_ago = datetime.datetime.now() - datetime.timedelta(days=40)
    first_date = datetime.datetime(2020, 9, 1)

    out_dir = config.HTML_REPORTS_DIR
    out_dir.mkdir(exist_ok=True)
    out_path = out_dir / 'situacion_covid_por_ca.html'
    write_html_report(out_path, date_range=[forty_days_ago, ten_days_ago])
