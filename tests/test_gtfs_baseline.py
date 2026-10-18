from datetime import date

import numpy as np
import pandas as pd

from src.audit_gtfs_baseline import active_services, distance_envelope, peak_concurrency, time_seconds


def test_gtfs_times_keep_after_midnight_on_original_service_day():
    result = time_seconds(pd.Series(["23:59:00", "24:01:00", "27:30:00"]))
    assert list(result) == [86340, 86460, 99000]
    assert peak_concurrency([86340, 86400], [86400, 86520]) == 1


def test_holiday_calendar_removes_regular_service_and_adds_exception():
    calendar = pd.DataFrame([dict(service_id="weekday", start_date="20230904", end_date="20231231",
                                 monday="1", tuesday="1", wednesday="1", thursday="1", friday="1", saturday="0", sunday="0")])
    exceptions = pd.DataFrame([dict(service_id="weekday", date="20231225", exception_type="2"),
                               dict(service_id="holiday", date="20231225", exception_type="1")])
    assert active_services(calendar, exceptions, date(2023, 12, 25)) == {"holiday"}
    assert active_services(calendar, exceptions, date(2023, 12, 26)) == {"weekday"}


def test_missing_origin_distance_is_an_interval_not_an_observed_zero():
    low, high = distance_envelope(np.array([np.nan, 2.0]), np.array([10.0, 8.0]),
                                  np.array([0.25, 2.0]), np.array([10.0, 8.0]),
                                  np.array([0.0, 0.0]), np.array([12.0, 12.0]))
    assert list(low) == [9.75, 6.0]
    assert list(high) == [10.0, 6.0]
