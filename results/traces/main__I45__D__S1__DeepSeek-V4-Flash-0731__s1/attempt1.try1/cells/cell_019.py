
# Check if Feb 29 dates are in pools of days 59 and 61
from datetime import datetime

# Find Feb 29 dates in baseline
feb29_dates = []
for d in base_dates:
    if d.month == 2 and d.day == 29:
        feb29_dates.append(d)
print("Feb 29 dates in baseline+ext:", feb29_dates)

# Check if they're in pools 59 and 61
for fd in feb29_dates:
    # Find index
    idx = np.where(base_dates == fd)[0]
    if len(idx) > 0:
        i = idx[0]
        in_59 = i in pool_indices[59]
        in_61 = i in pool_indices[61]
        print(f"  {fd}: in pool 59: {in_59}, in pool 61: {in_61}")
