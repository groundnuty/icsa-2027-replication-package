
import numpy as np
from datetime import date

# Baseline + window extension dates
start_baseline = date(1991, 12, 27)
end_baseline = date(2003, 1, 5)
n_baseline_days = (end_baseline - start_baseline).days + 1
print("Baseline days:", n_baseline_days)

# Target
start_target = date(2014, 6, 1)
end_target = date(2014, 8, 31)
n_target_days = (end_target - start_target).days + 1
print("Target days:", n_target_days)

# Region
n_lat = 60
n_lon = 60
n_cells = n_lat * n_lon
print("Cells:", n_cells)

# Memory estimate for baseline data
baseline_elems = n_baseline_days * n_cells
print("Baseline elements:", baseline_elems)
print("Baseline memory (float32):", baseline_elems * 4 / 1e6, "MB")
print("Baseline memory (float64):", baseline_elems * 8 / 1e6, "MB")
