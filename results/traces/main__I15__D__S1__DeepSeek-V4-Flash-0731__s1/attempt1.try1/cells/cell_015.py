
import xarray as xr
import numpy as np
import datetime
import pandas as pd

def date_to_doy(dt):
    """Fixed 366-day mapping: Jan=1..31, Feb=32..59/60, Mar=61..91, etc."""
    days_in_month = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    doy = sum(days_in_month[:dt.month-1]) + dt.day
    return doy

# Verify mapping
for d in [datetime.date(1992,1,1), datetime.date(1992,2,28), datetime.date(1992,2,29), 
          datetime.date(1992,3,1), datetime.date(1993,3,1), datetime.date(2019,12,31)]:
    print(d, "->", date_to_doy(d))
