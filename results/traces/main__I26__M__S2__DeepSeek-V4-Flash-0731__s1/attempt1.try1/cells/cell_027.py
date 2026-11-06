
import numpy as np

per_cell_mhw_A = np.load('/tmp/per_cell_mhw.npy')

# Check day 14 and 15 (indices 14, 15)
print("Day 14 (June 14) - cells in MHW under interpretation A:")
cells_14 = np.argwhere(per_cell_mhw_A[14])
print(f"  Count: {len(cells_14)}")
for c in cells_14[:5]:
    print(f"  Cell ({c[0]}, {c[1]})")

print("\nDay 15 (June 15) - cells in MHW under interpretation A:")
cells_15 = np.argwhere(per_cell_mhw_A[15])
print(f"  Count: {len(cells_15)}")
for c in cells_15[:5]:
    print(f"  Cell ({c[0]}, {c[1]})")

# Let me check what's happening with these cells
# The key question is whether these cells are in MHWs on days 14-15
# due to joining of short runs to longer runs

# Let me check one cell that's in an MHW on day 14
if len(cells_14) > 0:
    lat, lon = cells_14[0]
    print(f"\nExamining cell ({lat}, {lon}) on day 14:")
    print(f"  Is sea cell: {np.load('/tmp/sea_cells.npy')[lat, lon]}")
    
    # Look at the hot pattern for this cell
    hot = np.load('/tmp/hot.npy') if os.path.exists('/tmp/hot.npy') else None
    print(f"  Hot file exists: {hot is not None}")
