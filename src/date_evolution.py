
import config

import math
import datetime
import sys

import numpy
import pandas

from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
from matplotlib.figure import Figure

import data_sources


def build_report_date_dframe(ccaa_reports, parameter):
    #date, report_date, ccaa, parameter
    dframe = None
    for ccaa_report in ccaa_reports:
        this_dframe = ccaa_report['dframe']
        report_date = ccaa_report['datetime']
        series_for_parameter = this_dframe.loc[:, parameter]

        this_dframe = pandas.DataFrame({report_date: series_for_parameter},
                                        index=series_for_parameter.index)
        if dframe is None:
            dframe = this_dframe
        else:
            dframe = dframe.join(this_dframe, how='outer')

    dframe = dframe[sorted(dframe.columns)]
    return dframe


def get_unique_parameters(ccaa_reports):
    parameters = set()
    for report in ccaa_reports:
        parameters.update(list(report['dframe'].columns))
    parameters = parameters.difference(['cod_ine'])
    return parameters


def get_final_num_for_ccaa_and_date(report_date_dframe):
    final_date = max(list(report_date_dframe.columns))
    return report_date_dframe[final_date]


def calculate_percent_reported_per_ccaa_and_date(report_date_dframe):
    final_num_for_ccaa_and_date = get_final_num_for_ccaa_and_date(report_date_dframe)
    percent_reported = {}
    report_dates = sorted(report_date_dframe.columns)
    for report_date in report_dates:
        percent_reported[report_date] = report_date_dframe[report_date] / final_num_for_ccaa_and_date * 100
    percent_reported = pandas.DataFrame(percent_reported)
    percent_reported = percent_reported[report_dates]
    return percent_reported


def calculate_percent_reported_after_given_num_days(report_date_dframe, num_days):
    percent_reported = calculate_percent_reported_per_ccaa_and_date(report_date_dframe)
    dates = report_date_dframe.index.to_frame(index=False)['fecha'].values
    timedelta = numpy.timedelta64(num_days, 'D')
    dates_after_given_num_days = dates + timedelta

    mask_report_day_earlier_than_given_num_days = []
    for report_date in percent_reported.columns:
        this_col_mask = dates_after_given_num_days <= report_date
        mask_report_day_earlier_than_given_num_days.append(this_col_mask)
    mask_report_day_earlier_than_given_num_days = numpy.array(mask_report_day_earlier_than_given_num_days).T

    percent_reported[mask_report_day_earlier_than_given_num_days] = math.nan
    return percent_reported


def plot_percent_reported_per_ccaa_per_report_date(report_date_dframe, num_days, first_day, ccaas_to_report=None):

    percent_reported = calculate_percent_reported_after_given_num_days(report_date_dframe, 7)

    ccaas = sorted(set(percent_reported.index.to_frame(index=False)['ccaa']))
    report_dates = list(percent_reported.columns)

    mean_reported = {}
    for ccaa in ccaas:
        if ccaas_to_report is not None and ccaa not in ccaas_to_report:
            continue
        percent_reported_for_ccaa = percent_reported.loc[ccaa, :]
        mean_reported[ccaa]= [numpy.nanmean((percent_reported_for_ccaa[report_date])) for report_date in report_dates]

    fig = Figure()
    FigureCanvas(fig) # Don't remove it or savefig will fail later
    axes = fig.add_subplot(111)

    for ccaa, mean_reported_cases in mean_reported.items():
        axes.plot(report_dates, mean_reported_cases, label=ccaa)

    x_days_ago = datetime.date.today() + datetime.timedelta(days=-num_days)
    axes.set_xlim((first_day, x_days_ago))

    axes.legend()

    out_dir = config.PLOT_DIR
    out_dir.mkdir(exist_ok=True)
    plot_path = out_dir / f'num_casos_medios_reportados_despues_de_{num_days}_dias.svg'
    fig.tight_layout()
    fig.savefig(plot_path)


def get_added_cases_between_two_datasets(dset1, dset2, parameter):
    
    num_cases1 = dset1['dframe'][parameter]
    num_cases2 = dset2['dframe'][parameter]

    num_cases1 = num_cases1.reindex(num_cases2.index, fill_value=0)

    dates = numpy.datetime64(dset2['max_date']) - num_cases2.index.to_frame(index=False)['fecha']
    num_days_delayed = dates / numpy.timedelta64(1, 'D')

    diff = num_cases2 - num_cases1

    return {'diff_between_cases': diff, 'num_days_delayed': num_days_delayed}


def calc_mean_num_days_delay_by_ccaa(dset1, dset2, parameter, ignore_removed_cases=True):
    res = get_added_cases_between_two_datasets(dset1, dset2, parameter)
    num_days_delayed = res['num_days_delayed']
    diff_between_cases = res['diff_between_cases']

    ccaa_column = data_sources.get_ccaa_column_in_index(diff_between_cases.index)

    index = diff_between_cases.index.to_frame(index=False)

    means = []
    ccaas = data_sources.get_ccaas_in_dset(dset1)
    cases_added = []
    cases_removed = []
    for ccaa in ccaas:
        mask = index[ccaa_column] == ccaa
        mask = mask.values
        diff_between_cases_for_this_ccaa = diff_between_cases.loc[mask]

        cases_added_for_this_ccaa = numpy.sum(diff_between_cases_for_this_ccaa[diff_between_cases_for_this_ccaa > 0])
        cases_removed_for_this_ccaa = numpy.sum(diff_between_cases_for_this_ccaa[diff_between_cases_for_this_ccaa < 0])
        cases_added.append(cases_added_for_this_ccaa)
        cases_removed.append(cases_removed_for_this_ccaa)

        if ignore_removed_cases:
            diff_between_cases_for_this_ccaa[diff_between_cases_for_this_ccaa<0] = 0
        num_days_delayed_for_this_ccaa = num_days_delayed.loc[mask]
        mean = numpy.average(num_days_delayed_for_this_ccaa,
                             weights=diff_between_cases_for_this_ccaa)
        means.append(mean)

    means = pandas.Series(means, index=ccaas)
    cases_added = pandas.Series(cases_added, index=ccaas)
    cases_removed = pandas.Series(cases_removed, index=ccaas)
    return {'mean_delays': means, 'num_cases_added': cases_added, 'num_cases_removed': cases_removed}


def set_x_ticks(tick_poss, tick_labels, axes, rotation=0, ha='right', fontsize=10):
    axes.set_xticklabels(tick_labels, rotation=rotation, ha=ha, fontsize=fontsize)
    axes.set_xticks(tick_poss)


def plot_mean_delay_by_ccaa(sort_by='value'):
    fig = Figure((5, 7))
    FigureCanvas(fig) # Don't remove it or savefig will fail later
    axes = fig.add_subplot(211)

    ccaa_info = data_sources.get_sorted_downloaded_ccaa_info()
    res = calc_mean_num_days_delay_by_ccaa(ccaa_info[-2], ccaa_info[-1],
                                           parameter='num_casos')
    mean_delay = res['mean_delays']
    num_cases_added = res['num_cases_added']
    num_cases_removed = res['num_cases_removed']

    sorted_indexes = None
    if sort_by == 'value':
        sorted_indexes = numpy.flip(numpy.argsort(mean_delay.values))
    if sorted_indexes is not None:
        mean_delay = mean_delay.iloc[sorted_indexes]
        num_cases_added = num_cases_added.iloc[sorted_indexes]
        num_cases_removed = num_cases_removed.iloc[sorted_indexes]

    x_poss = numpy.arange(mean_delay.size)
    width = x_poss[1] - x_poss[0]

    axes.bar(x_poss, mean_delay, width=width)

    axes.set_ylabel('Retraso medio en casos añadidos (Num. días)')

    axes2 = fig.add_subplot(212)
    axes2.bar(x_poss, num_cases_added, width=width)
    axes2.bar(x_poss, num_cases_removed, width=width)
    axes2.set_ylabel('Num. casos añadidos/eliminados')

    set_x_ticks(x_poss,
                data_sources.convert_to_ccaa_names(mean_delay.index.values),
                axes2, rotation=45)

    out_dir = config.PLOT_DIR
    out_dir.mkdir(exist_ok=True)
    plot_path = out_dir / f'retraso_medio_en_casos_anyadidos.svg'
    fig.tight_layout()
    fig.savefig(plot_path)


def plot_delays_by_ccaa():
    ccaa_info = data_sources.get_sorted_downloaded_ccaa_info()

    dset1 = ccaa_info[-1]
    dset2 = ccaa_info[-2]

    res = get_added_cases_between_two_datasets(ccaa_info[-2], ccaa_info[-1],
                                               parameter='num_casos')
    num_days_delayed = res['num_days_delayed']
    diff_between_cases = res['diff_between_cases']

    ccaas = data_sources.get_ccaas_in_dset(dset1)
    ccaa_column = data_sources.get_ccaa_column_in_index(diff_between_cases.index)
    index = diff_between_cases.index.to_frame(index=False)

    out_dir = config.PLOT_DIR
    out_dir.mkdir(exist_ok=True)
    out_dir = out_dir / 'delays_per_ccaa'
    out_dir.mkdir(exist_ok=True)

    for ccaa in ccaas:
        mask = index[ccaa_column] == ccaa
        mask = mask.values
        diff_between_cases_for_this_ccaa = diff_between_cases.loc[mask]
        num_days_delayed_for_this_ccaa = num_days_delayed[mask]
        plot_path = out_dir / f'changes_in_num_cases_reported_{ccaa}.svg'
        fig = Figure()
        FigureCanvas(fig) # Don't remove it or savefig will fail later
        axes = fig.add_subplot(111)
        axes.bar(-num_days_delayed_for_this_ccaa, diff_between_cases_for_this_ccaa)

        axes.set_xlim((-50, 0))
        axes.set_ylabel('Núm. casos añadido/eliminados')
        axes.set_xlabel('Días de retraso')
        axes.set_title(data_sources.convert_to_ccaa_nam(ccaa))

        fig.tight_layout()
        fig.savefig(plot_path)


if __name__ == '__main__':

    ccaa_info = data_sources.get_sorted_downloaded_ccaa_info()
    calc_mean_num_days_delay_by_ccaa(ccaa_info[-2], ccaa_info[-1],
                                     parameter='num_casos')
    plot_mean_delay_by_ccaa()

    plot_delays_by_ccaa()


    sys.exit()

    ccaa_reports = list(data_sources.get_ccaa_datadista_info())
    parameters = get_unique_parameters(ccaa_reports)
    parameter = 'num_casos_prueba_pcr'
    report_date_dframe = build_report_date_dframe(ccaa_reports, parameter)
    #percent_reported = calculate_percent_reported_after_given_num_days(report_date_dframe, 7)
    ccaas = ['Madrid', 'Cataluña', 'C. Valenciana', 'Asturias', 'Galicia']
    plot_percent_reported_per_ccaa_per_report_date(report_date_dframe, 15,
                                                   first_day=datetime.datetime(2020, 9, 1),
                                                   ccaas_to_report=ccaas)

    
    # Distribución número de cambios vs número de días entre dos informes
    # Incidencia acumulada calculada con los números finales y con los números que se dieron el día correspondiente al ministerio. Diferencia entre ambas medidas

