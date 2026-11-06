
import numpy as np

target_data = np.load('/tmp/target_data.npy')
threshold = np.load('/tmp/threshold.npy')
sea_mask = np.load('/tmp/sea_mask.npy')
hot = np.load('/tmp/hot.npy')

# Cell (52, 25)
i, j = 52, 25
print(f"Cell ({i},{j}): sea={sea_mask[i,j]}")

# Check SST values around days 60-61
for t in range(55, 68):
    doy = 153 + t  # DOY for day t
    sst = target_data[t, i, j]
    thr = threshold[i, j, doy-1]
    is_hot = hot[i, j, t]
    print(f"  Day {t} (DOY {doy}): SST={sst:.4f}, threshold={thr:.4f}, hot={is_hot}")

# Check DOY mapping
print("\nDOY verification:")
print(f"  Jul 31 = DOY {213}")
print(f"  Aug 1 = DOY {214}")
print(f"  Aug 2 = DOY {215}")
