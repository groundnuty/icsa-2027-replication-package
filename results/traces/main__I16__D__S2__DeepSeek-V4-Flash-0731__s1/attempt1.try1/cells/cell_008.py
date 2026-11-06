
import numpy as np
from datetime import date

def day_of_year(month, day):
    """Map (month, day) to day of year 1-366 using 366-day calendar.
    Jan=1..31, Feb=32..59, Feb29=60, Mar=61.., Dec 31=366."""
    cum = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
    # cum[m] = days before month m (1-indexed)
    # For Feb (m=2), cum = 31
    # For Mar (m=3), cum = 60 (including Feb 29 in the abstract calendar)
    return cum[month-1] + day

# Verify
print(day_of_year(1,1), day_of_year(2,28), day_of_year(2,29), day_of_year(3,1), day_of_year(12,31))
