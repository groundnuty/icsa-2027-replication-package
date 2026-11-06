
import numpy as np
import pickle

# Load saved data
baseline_data = np.load('/tmp/baseline_data.npy')
target_data = np.load('/tmp/target_data.npy')
with open('/tmp/dates.pkl', 'rb') as f:
    dates = pickle.load(f)

baseline_dates = dates['baseline_dates']
target_dates = dates['target_dates']

print(f"baseline_data: {baseline_data.shape}")
print(f"target_data: {target_data.shape}")
print(f"baseline dates: {baseline_dates[0]} to {baseline_dates[-1]}, count={len(baseline_dates)}")
print(f"target dates: {target_dates[0]} to {target_dates[-1]}, count={len(target_dates)}")
