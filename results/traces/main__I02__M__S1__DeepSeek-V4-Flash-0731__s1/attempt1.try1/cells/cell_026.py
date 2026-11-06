
import numpy as np

hot = np.load('/tmp/hot.npy')
sea_mask = np.load('/tmp/sea_mask.npy')

# Check hot day distribution
print("Hot days per cell:")
hot_counts = hot.sum(axis=2)
for i in range(60):
    for j in range(60):
        if sea_mask[i,j] and hot_counts[i,j] > 0:
            hot_days = np.where(hot[i,j,:])[0]
            print(f"  Cell ({i},{j}): hot days at target indices {hot_days}, dates would be...")

# Print the actual dates for these hot days
with open('/tmp/dates.pkl', 'rb') as f:
    import pickle
    dates = pickle.load(f)
target_dates = dates['target_dates']

for i in range(60):
    for j in range(60):
        if sea_mask[i,j] and hot_counts[i,j] > 0:
            hot_days = np.where(hot[i,j,:])[0]
            dates_str = [str(target_dates[t]) for t in hot_days]
            print(f"  Cell ({i},{j}): {hot_counts[i,j]} hot days: {dates_str}")
