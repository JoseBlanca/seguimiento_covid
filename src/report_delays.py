
import datetime
import math

import numpy
import pandas

import ministry_datasources
import data_sources


def get_consecutive_reports(kind):
    if kind == 'deceased':
        reports = ministry_datasources.get_sorted_deceased_excel_ministry_files()
    elif kind == 'reported_cases':
        reports = data_sources.get_sorted_downloaded_ccaa_info()
        for report in reports:
            dframe = report['dframe'].loc[:, 'num_casos'].unstack(level=1)
            report['dframe'] = dframe

    max_delay = datetime.timedelta(days=1)

    report_pairs = [(report2, report1) for report1, report2 in zip(reports[:-1], reports[1:]) if report2['max_date'] - report1['max_date'] <= max_delay]
    return report_pairs


def calculate_differences_between_two_reports(report2, report1):
    dframe2 = report2['dframe']
    dframe1 = report1['dframe']
    assert list(dframe2.index) == list(dframe1.index)

    dframe1 = dframe1.reindex(dframe2.index)
    diffs = dframe2 - dframe1
    diffs = diffs.dropna(axis='columns', how='all')
    return diffs


#taken from https://gist.github.com/tinybike
def weighted_median(data, weights):
    """
    Args:
      data (list or numpy.array): data
      weights (list or numpy.array): weights
    """
    data, weights = numpy.array(data).squeeze(), numpy.array(weights).squeeze()
    s_data, s_weights = map(numpy.array, zip(*sorted(zip(data, weights))))
    midpoint = 0.5 * sum(s_weights)
    if any(weights > midpoint):
        w_median = (data[weights == numpy.max(weights)])[0]
    else:
        cs_weights = numpy.cumsum(s_weights)
        idx = numpy.where(cs_weights <= midpoint)[0][-1]
        if cs_weights[idx] == midpoint:
            w_median = numpy.mean(s_data[idx:idx+2])
        else:
            w_median = s_data[idx+1]
    return w_median


def calculate_median_delays_in_added_cases_per_ccaa(report_kind):

    consecutive_report_pairs = get_consecutive_reports(report_kind)

    median_delays_for_all_report_pairs = {}
    for report2, report1 in consecutive_report_pairs:
        diffs_in_num_cases = calculate_differences_between_two_reports(report2, report1)
        diffs_in_num_cases[diffs_in_num_cases < 0] = 0
        dates = diffs_in_num_cases.columns.to_frame(index=False).values[:, 0]
        num_days_delayed = (dates[-1] - dates) / numpy.timedelta64(1, 'D')

        median_delays = []
        ccaas = []
        for ccaa, diffs_in_num_cases_for_this_ccaa in diffs_in_num_cases.iterrows():
            if numpy.sum(diffs_in_num_cases_for_this_ccaa):    
                median = weighted_median(num_days_delayed, diffs_in_num_cases_for_this_ccaa.values)
            else:
                median = math.nan
            median_delays.append(median)
            ccaas.append(ccaa)
        median_delays = pandas.Series(median_delays, index=ccaas)

        median_delays_for_all_report_pairs[report2['max_date']] = median_delays

    median_delays = pandas.DataFrame(median_delays_for_all_report_pairs)
    return median_delays


if __name__ == '__main__':
    
    #calculate_median_delays_in_added_cases_per_ccaa('deceased')
    calculate_median_delays_in_added_cases_per_ccaa('reported_cases')