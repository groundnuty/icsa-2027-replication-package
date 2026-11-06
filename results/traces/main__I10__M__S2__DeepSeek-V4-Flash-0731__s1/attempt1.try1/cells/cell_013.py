
import numpy as np

# Check if cell (0,0) is a sea cell
print("sea_cells[0,0]:", sea_cells[0,0])

# Check the raw thresholds for cell (0,0) across doys
for d in [1, 10, 58, 59, 60, 61, 100, 200, 300, 366]:
    if d == 60:
        print(f"doy {d}: {thresholds[d-1, 0, 0]:.6f}")
    else:
        print(f"doy {d}: {thresholds[d-1, 0, 0]:.6f}")

# Check a different cell
print("\nCell (30, 30):")
print("sea_cells[30,30]:", sea_cells[30,30])
for d in [1, 10, 58, 59, 60, 61, 100, 200, 300, 366]:
    print(f"doy {d}: {thresholds[d-1, 30, 30]:.6f}")
