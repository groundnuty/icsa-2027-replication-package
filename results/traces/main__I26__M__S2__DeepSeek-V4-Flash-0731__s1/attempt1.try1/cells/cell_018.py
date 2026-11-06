
import numpy as np

# Load saved data
per_cell_mhw = np.load('/tmp/per_cell_mhw.npy')
sea_cells = np.load('/tmp/sea_cells.npy')

# Find cells with MHWs
cells_with_mhw = per_cell_mhw.any(axis=0)
print(f"Cells with MHW: {cells_with_mhw.sum()}")
print(f"Total sea cells: {sea_cells.sum()}")

# Find the cell with the most MHW days
cell_counts = per_cell_mhw.sum(axis=0)
max_cell = np.unravel_index(np.argmax(cell_counts), cell_counts.shape)
print(f"Cell with most MHW days: ({max_cell[0]}, {max_cell[1]}), count: {cell_counts[max_cell]}")
print(f"Is sea cell: {sea_cells[max_cell]}")

# Show MHW pattern for this cell
print(f"\nMHW pattern for cell ({max_cell[0]}, {max_cell[1]}):")
for t in range(92):
    if per_cell_mhw[t, max_cell[0], max_cell[1]]:
        print(f"  Day {t}: MHW active")
