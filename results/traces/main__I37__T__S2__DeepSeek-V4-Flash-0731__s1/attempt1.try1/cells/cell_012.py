
import pandas as pd
import numpy as np
from datetime import datetime

# Fixed day-of-year mapping
def fixed_doy(date):
    cum = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
    return cum[date.month-1] + date.day

# Verify
for dt_str in ['2020-01-01', '2020-02-28', '2020-02-29', '2020-03-01', '2020-12-31', '2019-02-28', '2019-03-01']:
    d = pd.Timestamp(dt_str)
    print(f"{dt_str}: doy={fixed_doy(d)}")
