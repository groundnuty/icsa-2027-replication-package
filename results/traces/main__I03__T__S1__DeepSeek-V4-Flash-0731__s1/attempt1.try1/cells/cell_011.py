
import numpy as np
import datetime

# Load data
baseline_vals = np.load('baseline_vals.npy')  # (4028, 60, 60)
target_vals = np.load('target_vals.npy')  # (92, 60, 60)
baseline_dates = np.load('baseline_dates.npy', allow_pickle=True)  # strings
target_dates = np.load('target_dates.npy', allow_pickle=True)

# Convert to datetime objects
baseline_dt = [datetime.datetime.strptime(d, 'YYYY-MM-DD') for d in baseline_dates]
print("First few baseline dates:", baseline_dt[:3])
print("Last few baseline dates:", baseline_dt[-3:])
print("Type of baseline_dates[0]:", type(baseline_dates[0]))
