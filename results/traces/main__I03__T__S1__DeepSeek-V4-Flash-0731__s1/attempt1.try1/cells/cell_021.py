
import numpy as np
import datetime

# Load data
target_vals = np.load('target_vals.npy')  # (92, 60, 60)
target_dates_str = np.load('target_dates.npy', allow_pickle=True)
target_dt = [datetime.datetime.strptime(str(s), '%Y-%m-%d') for s in target_dates_str]

def day_of_year(dt):
    month_offsets = [0, 0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
    return month_offsets[dt.month] + dt.day

# Print target dates and their day-of-year
for i, dt in enumerate(target_dt):
    doy = day_of_year(dt)
    print(f"Day {i}: {dt.strftime('%Y-%m-%d')} -> doy {doy}")

print(f"\nTarget vals shape: {target_vals.shape}")
print(f"Target finite count: {np.isfinite(target_vals).sum()} / {target_vals.size}")
