
import numpy as np
# sst_target shape (92, 60, 60)
# Check which cells are sea cells (finite on all target days)
sea_cells = ~np.isnan(sst_target).any(axis=0)
print("Sea cells:", sea_cells.sum(), "out of", sea_cells.size)
print("Sea cell indices (lat, lon):")
# Count sea cells per lat/lon
print("Per lat:", sea_cells.sum(axis=1))
print("Per lon:", sea_cells.sum(axis=0))
