
import numpy as np

# Load raw threshold and check for NaN in sea cells
threshold_raw = np.load('output/threshold_raw.npy')  # (366, 60, 60)
sea_cells = np.load('output/sea_cells.npy')  # (60, 60)

# Check: do any sea cells have NaN in the raw threshold for any day?
# First, set day 60 (index 59)
threshold_with_d60 = threshold_raw.copy()
threshold_with_d60[59] = (threshold_raw[58] + threshold_raw[60]) / 2.0

# Check for NaN in sea cells
nan_in_sea = np.zeros((366, 60, 60), dtype=bool)
for d in range(366):
    for lat in range(60):
        for lon in range(60):
            if sea_cells[lat, lon] and np.isnan(threshold_with_d60[d, lat, lon]):
                nan_in_sea[d, lat, lon] = True

# Find days with NaN in any sea cell
days_with_nan = np.where(nan_in_sea.any(axis=(1, 2)))[0]
print(f"Days of year with NaN in threshold for some sea cell: {len(days_with_nan)}")
if len(days_with_nan) > 0:
    print(f"Day-of-year indices: {days_with_nan}")
    print(f"Day-of-year values (1-indexed): {days_with_nan + 1}")
    
    # Check specifically for the target period range (days 138-259)
    relevant = [d for d in days_with_nan if 137 <= d <= 259]
    print(f"NaN days in range 138-259 (1-indexed): {[d+1 for d in relevant]}")
    if relevant:
        # Show which cells have NaN
        for d in relevant:
            cells = np.where(nan_in_sea[d])[0]
            print(f"  Day {d+1}: {len(cells)} sea cells with NaN threshold")
else:
    print("No sea cell has NaN in threshold for any day of year")
