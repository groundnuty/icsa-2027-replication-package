
import numpy as np
from datetime import date, timedelta
import xarray as xr
import pandas as pd
from collections import defaultdict

# Verify day-of-year mapping
CUM = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
def doy_from_md(month, day):
    return CUM[month-1] + day

def get_doy(d):
    return doy_from_md(d.month, d.day)

# Verify key dates
test_cases = [
    (date(2000,1,1), 1),
    (date(2000,2,28), 59),
    (date(2000,2,29), 60),
    (date(2000,3,1), 61),
    (date(2000,12,31), 366),
    (date(2021,6,1), 153),  # Jun 1 = 31+29+31+30+31+1 = 153
    (date(2021,8,31), 244),  # Aug 31 = 31+29+31+30+31+30+31+31 = 244
]
for d, expected in test_cases:
    got = get_doy(d)
    status = "OK" if got == expected else "FAIL"
    print(f"{d}: doy={got}, expected={expected} {status}")

# Verify Jun 1: Jan 31 + Feb 28 + Mar 31 + Apr 30 + May 31 = 151, so Jun 1 = 152? 
# Wait, let me recount.
# Jan: 31 days -> Jan 1=1, Jan 31=31
# Feb: Feb 1=32, Feb 28=59
# Mar: Mar 1=61 (since Feb 29=60), Mar 31=91
# Apr: Apr 1=92, Apr 30=121
# May: May 1=122, May 31=152
# Jun: Jun 1=153, Jun 30=182
# Jul: Jul 1=183, Jul 31=213
# Aug: Aug 1=214, Aug 31=244
print("Jun 1 = 153, Aug 31 = 244 (verify with CUM: [0,31,60,91,121,152,182,213,244,274,305,335])")
print("Jun 1: CUM[5]+1 = 152+1 =", CUM[5]+1)
print("Aug 31: CUM[7]+31 = 213+31 =", CUM[7]+31)
