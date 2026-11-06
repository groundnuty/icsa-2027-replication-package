
import numpy as np
import pandas as pd
import json

# Load thresholds and climatology
thresholds_smooth = np.load('/work/thresholds_smooth.npy')
climatology_smooth = np.load('/work/climatology_smooth.npy')
sea_cells = np.load('/work/sea_cells.npy')

# Get sea cell stats
sea_indices = np.argwhere(sea_cells)
sea_thresholds = thresholds_smooth[sea_indices[:, 0], sea_indices[:, 1], :]
sea_clim = climatology_smooth[sea_indices[:, 0], sea_indices[:, 1], :]

print("Threshold stats (sea cells):")
print(f"  Overall min: {np.nanmin(sea_thresholds):.2f} K")
print(f"  Overall max: {np.nanmax(sea_thresholds):.2f} K")
print(f"  Overall mean: {np.nanmean(sea_thresholds):.2f} K")

print("\nClimatology stats (sea cells):")
print(f"  Overall min: {np.nanmin(sea_clim):.2f} K")
print(f"  Overall max: {np.nanmax(sea_clim):.2f} K")
print(f"  Overall mean: {np.nanmean(sea_clim):.2f} K")

# Check for target period doys
target_doys = np.array([153, 154, 155, 156, 157, 158, 159, 160, 161, 162, 163, 164, 165, 166, 167, 168, 169, 170, 171, 172, 173, 174, 175, 176, 177, 178, 179, 180, 181, 182, 183, 184, 185, 186, 187, 188, 189, 190, 191, 192, 193, 194, 195, 196, 197, 198, 199, 200, 201, 202, 203, 204, 205, 206, 207, 208, 209, 210, 211, 212, 213, 214, 215, 216, 217, 218, 219, 220, 221, 222, 223, 224, 225, 226, 227, 228, 229, 230, 231, 232, 233, 234, 235, 236, 237, 238, 239, 240, 241, 242, 243, 244])
target_thresholds = thresholds_smooth[sea_indices[:, 0], sea_indices[:, 1], target_doys - 1]
target_clim = climatology_smooth[sea_indices[:, 0], sea_indices[:, 1], target_doys - 1]

print("\nTarget period threshold stats:")
print(f"  Min: {np.nanmin(target_thresholds):.2f} K")
print(f"  Max: {np.nanmax(target_thresholds):.2f} K")
print(f"  Mean: {np.nanmean(target_thresholds):.2f} K")

print("\nTarget period climatology stats:")
print(f"  Min: {np.nanmin(target_clim):.2f} K")
print(f"  Max: {np.nanmax(target_clim):.2f} K")
print(f"  Mean: {np.nanmean(target_clim):.2f} K")

# Check target SST values
target_data = np.load('/work/target_data.npy')
sea_target = target_data[:, sea_indices[:, 0], sea_indices[:, 1]]
print(f"\nTarget SST stats:")
print(f"  Min: {np.nanmin(sea_target):.2f} K")
print(f"  Max: {np.nanmax(sea_target):.2f} K")
print(f"  Mean: {np.nanmean(sea_target):.2f} K")
