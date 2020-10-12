
import config

import datetime

import numpy
import pandas


CA_NAMES_FOR_ISO_CODES = {'AN': 'Andalucía',
'AR': 'Aragón',
'AS': 'Asturias',
'CN': 'Canarias',
'CB': 'Cantabria',
'CM': 'Castilla La Mancha',
'CL': 'Castilla y León',
'CT': 'Cataluña',
'EX': 'Extremadura',
'GA': 'Galicia',
'IB': 'Islas Baleares',
'RI': 'La Rioja',
'MD': 'Madrid',
'MC': 'Murcia',
'NC' : 'Navarra',
'PV' : 'País Vasco',
'VC': 'Comunidad Valenciana',
'CE': 'Ceuta',
'ML': 'Melilla'}

ISO_CODES_FOR_CA = {ccaa: iso_code for iso_code, ccaa in CA_NAMES_FOR_ISO_CODES.items()}

CA_NAMES_FOR_ISO_CODES.update({
'Andalucía': 'Andalucía',
'Aragón': 'Aragón',
'Asturias': 'Asturias',
'Canarias': 'Canarias',
'Cantabria': 'Cantabria',
'Castilla La Mancha': 'Castilla La Mancha',
'Castilla y León': 'Castilla y León',
'Cataluña': 'Cataluña',
'Extremadura': 'Extremadura',
'Galicia': 'Galicia',
'Baleares': 'Islas Baleares',
'La Rioja': 'La Rioja',
'Madrid': 'Madrid',
'Murcia': 'Murcia',
'Navarra' : 'Navarra',
'País Vasco' : 'País Vasco',
'C. Valenciana': 'Comunidad Valenciana',
'Ceuta': 'Ceuta',
'Melilla': 'Melilla',
})


POPULATION = {
'AN': 8446561,
'AR': 1324397,
'AS': 1019993,
'CB': 581949,
'CE': 84434,
'CL': 2402877,
'CM': 2038440,
'CN': 2220270,
'CT': 7609499,
'EX': 1062797,
'GA': 2698764,
'IB': 1198576,
'MC': 1494442,
'MD': 6685471,
'ML': 84286,
'NC': 652526,
'PV': 2181919,
'RI': 314487,
'VC': 4998711,
}


def get_population(ccaa):
    return POPULATION[convert_to_ccaa_iso(ccaa)]


def convert_to_ccaa_iso(ccaa):
    return ISO_CODES_FOR_CA[CA_NAMES_FOR_ISO_CODES[ccaa]]

def convert_to_ccaa_name(ccaa):
    return CA_NAMES_FOR_ISO_CODES[ccaa]


def convert_to_ccaa_names(list_of_ccaas):
    return [convert_to_ccaa_name(ccaa) for ccaa in list_of_ccaas]


def date_parse(date):
    return datetime.datetime.strptime(date, '%Y-%m-%d')


def read_ccaa_csv(path, ccaa_column):
    data = pandas.read_csv(path, index_col=[ccaa_column, 'fecha'], parse_dates=['fecha'], date_parser=date_parse)
    return data


def get_num_cases_columns(dframe):
    return [col for col in dframe.columns if 'num_casos' in col]


def get_ccaa_dataset(path, ccaa_column):
    try:
        timestamp = int(path.stem.split('.')[0])
    except ValueError:
        timestamp = None
    if timestamp is not None:
        timestamp_datetime = datetime.datetime.utcfromtimestamp(timestamp)
    else:
        timestamp_datetime = None

    data = read_ccaa_csv(path, ccaa_column=ccaa_column)

    max_date = max(data.index.to_frame(index=False)['fecha'])
    max_date = max_date.date()

    result = {'dframe': data, 'max_date': max_date}

    if timestamp_datetime:
        result['file_timestamp_datetime'] = timestamp_datetime
    return result


def get_ccaa_datadista_info(timestamps_to_exclude=config.DATADISTA_TIMESTAMPS_TO_EXCLUDE):

    for path in config.DATADISTA_DIR.iterdir():
        if str(path).startswith('.~lock'):
            continue
        timestamp = int(path.stem.split('.')[0])
        if timestamp in timestamps_to_exclude:
            continue
        yield get_ccaa_dataset(path, ccaa_column='ccaa')


def get_downloaded_ccaa_info():
    
    for path in config.DOWNLOADED_DATASETS_DIR.iterdir():
        if 'ccaa' not in str(path):
            continue
        if path.stem.startswith('.~lock'):
            continue
        yield get_ccaa_dataset(path, ccaa_column='ccaa_iso')


def get_sorted_downloaded_ccaa_info(filter_out_reports_with_same_max_date=True):
    reports = get_downloaded_ccaa_info()

    if filter_out_reports_with_same_max_date:
        dates = set()
        flt_reports = []
        for report in reports:
            if report['max_date'] in dates:
                continue
            dates.add(report['max_date'])
            flt_reports.append(report)
        reports = flt_reports

    return sorted(reports, key=lambda x: x['max_date'])


def get_ccaa_column_in_index(index):
    index = index.to_frame(index=False)
    if 'ccaa' in index.columns:
        ccaa_column = 'ccaa'
    elif 'ccaa_iso' in index.columns:
        ccaa_column = 'ccaa_iso'
    else:
        raise ValueError('dframe has no known ccaa index')
    return ccaa_column


def get_ccaas_in_dset(dset):
    index = dset['dframe'].index
    ccaa_column = get_ccaa_column_in_index(index)

    return sorted(numpy.unique(index.to_frame(index=False)[ccaa_column].values))


if __name__ == '__main__':
    reports = get_sorted_downloaded_ccaa_info()
    print([report['max_date'] for report in reports])
    #print(len(list(get_ccaa_datadista_info(timestamps_to_exclude=config.DATADISTA_TIMESTAMPS_TO_EXCLUDE))))
    #print(len(list(get_downloaded_ccaa_info())))
