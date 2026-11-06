
# Let me verify some intermediate values and edge cases
import numpy as np
import datetime
import pandas as pd

def date_to_doy(dt):
    days_in_month = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    doy = sum(days_in_month[:dt.month-1]) + dt.day
    return doy

# Check target doys
for d in [datetime.date(2019,6,1), datetime.date(2019,6,15), datetime.date(2019,7,1), 
          datetime.date(2019,8,1), datetime.date(2019,8,31)]:
    print(f"{d}: doy={date_to_doy(d)}")

# The target period 2019-06-01 to 2019-08-31 gives doys 153 to 244

# Let me also check whether the report baseline_analysed is correct.
# The pools include data from 1991-12-27 (window for doy 1) to 2003-01-05 (window for doy 366).
# But is the "baseline_analysed" the actual first/last day used in the pool computation?
# Looking at the pool for doy 1, it starts at 1991-12-27. For doy 366, it ends at 2003-01-05.
# So baseline_analysed should be 1991-12-27 to 2003-01-05. That's what I used.

print("\nCheck: first pool dates for each doy")
print("doy 1 first date:", datetime.date(1991,12,27))
print("doy 366 last date:", datetime.date(2003,1,5))
