
import datetime
import unittest
import math

import numpy
import pandas


class ParamDateEvolution:
    def __init__(self, cumulative_cases=None, incremental_cases=None):
        if cumulative_cases is None and incremental_cases is None:
            raise ValueError('Either cumulative or incremental cases should be given')
        if cumulative_cases is not None and incremental_cases is not None:
            msg = 'Either cumulative or incremental cases should be given, but not both'
            raise ValueError(msg)

        if cumulative_cases is not None:
            self._cumulative_cases = cumulative_cases
            self._incremental_cases = None
            dates = cumulative_cases.index.to_frame(index=False).values.flat
            num_days_in_period = None
        if incremental_cases is not None:
            self._cumulative_cases = None
            self._incremental_cases = incremental_cases
            dates = incremental_cases.index.to_frame(index=False).values.flat
            num_days_in_period = numpy.array([numpy.nan] + list((dates[1:] - dates[:-1]) / numpy.timedelta64(1, 'D')))
        self._num_days_in_period = num_days_in_period

    @property
    def cumulative_cases(self):
        if self._cumulative_cases is not None:
            return self._cumulative_cases
        
        incr_cases = self._incremental_cases
        cum_cases = incr_cases.cumsum(axis=0)
        self._cumulative_cases = cum_cases
        return cum_cases

    @property
    def incremental_cases(self):
        if self._incremental_cases is not None:
            return self._incremental_cases

        cum_cases = self.cumulative_cases.values
        incr_cases = cum_cases[1:, :]- cum_cases[:-1, :]
        dates = numpy.array(self.cumulative_cases.index.to_frame(index=False).values.flat)
        incr_cases = pandas.DataFrame(incr_cases,
                                      index=dates[1:],
                                      columns=self.cumulative_cases.columns)              
        self._incremental_cases = incr_cases
        self._num_days_in_period = (dates[1:] - dates[:-1]) / numpy.timedelta64(1, 'D')
        return incr_cases

    @property
    def num_days_incremental_period(self):
        if self._num_days_in_period is None:
            self.incremental_cases
        return self._num_days_in_period

    @property
    def daily_increments(self):
        incr_cases = self.incremental_cases
        num_days_in_period = self.num_days_incremental_period
        dates_for_periods = incr_cases.index.to_frame().values.flat

        if math.isnan(num_days_in_period[0]):
            num_days_in_period = num_days_in_period[1:]
            incr_cases = incr_cases.iloc[1:, :]
            dates_for_periods = dates_for_periods[1:]

        num_cols = incr_cases.shape[1]
        num_days_in_period = numpy.reshape(numpy.repeat(num_days_in_period, num_cols),
                                           (num_days_in_period.shape[0], num_cols))

        daily_increments_per_period = incr_cases / num_days_in_period
        daily_increments_per_period = pandas.DataFrame(daily_increments_per_period,
                                                       index=dates_for_periods)

        date_range = pandas.date_range(dates_for_periods[0], dates_for_periods[-1],
                                       freq='1D')

        last_daily_increment = None
        daily_increments = []
        for date1 in date_range:
            try:
                last_daily_increment = daily_increments_per_period.loc[date1, :]
            except KeyError:
                pass
            daily_increments.append(last_daily_increment)
        daily_increments = pandas.DataFrame(daily_increments, index=date_range)
        return daily_increments


class EvolutionTest(unittest.TestCase):
    def test_init(self):
        dates = [datetime.datetime(year=2020, month=7, day=1),
                 datetime.datetime(year=2020, month=7, day=2),
                 datetime.datetime(year=2020, month=7, day=4),
                 datetime.datetime(year=2020, month=7, day=5),
                 datetime.datetime(year=2020, month=7, day=6),
                ]
        cases1 = numpy.array([100, 200, 400, 500, 700])
        cases2 = cases1 + 100
        cases = pandas.DataFrame({'country1': cases1,
                                  'country2': cases2},
                                  index=dates)
        cases_evol = ParamDateEvolution(cumulative_cases=cases)
        incr_cases = cases_evol.incremental_cases
        expected_incrs = cases1[1:] - cases1[:-1]
        expected_incrs = numpy.array([expected_incrs, expected_incrs]).T
        assert numpy.all(incr_cases.values == expected_incrs)

        dates1 = incr_cases.index.to_frame().values.flat
        dates2 = cases.index.to_frame().values.flat[1:]
        assert numpy.all(dates1 == dates2)

        cases_evol2 = ParamDateEvolution(incremental_cases=incr_cases)
        expected_cum_cases = [100, 300, 400, 600]
        expected_cum_cases = numpy.array([expected_cum_cases, expected_cum_cases]).T
        assert numpy.all(cases_evol2.cumulative_cases.values == expected_cum_cases)

    def test_daily_increments(self):
        dates = [datetime.datetime(year=2020, month=7, day=1),
                 datetime.datetime(year=2020, month=7, day=2),
                 datetime.datetime(year=2020, month=7, day=4),
                 datetime.datetime(year=2020, month=7, day=5),
                 datetime.datetime(year=2020, month=7, day=6),
                ]
        cases1 = numpy.array([100, 100, 200, 100, 100])
        cases2 = cases1 * 2
        cases = pandas.DataFrame({'country1': cases1,
                                  'country2': cases2},
                                  index=dates)
        cases_evol = ParamDateEvolution(incremental_cases=cases)
        incr_cases = cases_evol.daily_increments
        expected = numpy.array([[100., 200.],
                                [100., 200.],
                                [100., 200.],
                                [100., 200.],
                                [100., 200.]])
        assert numpy.allclose(incr_cases.values, expected)
        assert [pandas.to_datetime(date).day for date in incr_cases.index] == [2, 3, 4, 5, 6]

    def test_daily_increments_from_cumulative_cases(self):
        dates = [datetime.datetime(year=2020, month=7, day=1),
                 datetime.datetime(year=2020, month=7, day=2),
                 datetime.datetime(year=2020, month=7, day=4),
                 datetime.datetime(year=2020, month=7, day=5),
                 datetime.datetime(year=2020, month=7, day=6),
                ]
        cases1 = numpy.array([100, 200, 400, 500, 700])
        cases2 = cases1 *2
        cases = pandas.DataFrame({'country1': cases1,
                                  'country2': cases2},
                                  index=dates)
        cases_evol = ParamDateEvolution(cumulative_cases=cases)
        incr_cases = cases_evol.daily_increments
        expected = numpy.array([[100., 200.],
                                [100., 200.],
                                [100., 200.],
                                [100., 200.],
                                [200., 400.]])
        assert numpy.allclose(incr_cases.values, expected)
        assert [pandas.to_datetime(date).day for date in incr_cases.index] == [2, 3, 4, 5, 6]


if __name__ == '__main__':
    unittest.main()
