
import numpy as np
import datetime

# Load data
baseline_vals = np.load('baseline_vals.npy')  # (4028, 60, 60)
target_vals = np.load('target_vals.npy')  # (92, 60, 60)
baseline_dates = np.load('baseline_dates.npy', allow_pickle=True)  # strings
target_dates = np.load('target_dates.npy', allow_pickle=True)

print("baseline_dates[0]:", repr(baseline_dates[0]))
print("baseline_dates[1]:", repr(baseline_dates[1]))
print("baseline_dates[-1]:", repr(baseline_dates[-1]))
print("target_dates[0]:", repr(target_dates[0]))
print("target_dates[-1]:", repr(target_dates[-1]))
