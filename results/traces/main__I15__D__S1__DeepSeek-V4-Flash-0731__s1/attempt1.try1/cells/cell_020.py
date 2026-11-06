
import numpy as np
import datetime
import pandas as pd

# Continue from previous state - need to recompute
# Let me write the full computation in one script

def date_to_doy(dt):
    days_in_month = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    doy = sum(days_in_month[:dt.month-1]) + dt.day
    return doy

# Target dates and their doys
target_dates = []
for m, d in [(6,i) for i in range(1,31)] + [(7,i) for i in range(1,32)] + [(8,i) for i in range(1,32)]:
    target_dates.append(datetime.date(2019, m, d))

target_doys = [date_to_doy(dt) for dt in target_dates]
print("Target dates doys:", target_doys[0], "...", target_doys[-1])
print("Count:", len(target_doys))
