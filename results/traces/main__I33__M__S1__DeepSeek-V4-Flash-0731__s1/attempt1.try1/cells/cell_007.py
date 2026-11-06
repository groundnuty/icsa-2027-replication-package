
from datetime import datetime, timedelta

# Fixed day-of-year mapping by month and day
# Jan=1-31, Feb=32-59(28th), Feb 29=60, Mar=61-91, Apr=92-121, May=122-152,
# Jun=153-182, Jul=183-213, Aug=214-244, Sep=245-274, Oct=275-305, Nov=306-335, Dec=336-366

# starts[month] = doy(month, 1) - 1
starts = [0, 0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]

def doy(month, day):
    return starts[month] + day

# Verify
print(f"Jan 1: {doy(1,1)}")  # 1
print(f"Jan 31: {doy(1,31)}")  # 31
print(f"Feb 1: {doy(2,1)}")  # 32
print(f"Feb 28: {doy(2,28)}")  # 59
print(f"Feb 29: {doy(2,29)}")  # 60
print(f"Mar 1: {doy(3,1)}")  # 61
print(f"Mar 31: {doy(3,31)}")  # 91
print(f"Apr 1: {doy(4,1)}")  # 92
print(f"Jun 1: {doy(6,1)}")  # 153
print(f"Dec 31: {doy(12,31)}")  # 366
print(f"Aug 1: {doy(8,1)}")  # 214
print(f"Oct 1: {doy(10,1)}")  # 275

# Now, for the baseline period, compute doy for each date
# Baseline dates: 1991-12-27 to 2003-01-05
# But the baseline years are 1992-2002

# For each date, doy is fixed based on month and day
# Jan 1 = 1, Dec 31 = 366 always

# Day 60 = Feb 29 (only exists in leap years)
# In non-leap years, there's no day 60, but day 59 (Feb 28) and day 61 (Mar 1) still exist
