
# Check what's in memory
print("Starting fresh check")
import sys
# Try to access previously defined variables
try:
    print("baseline_sst:", baseline_sst.shape)
except:
    print("baseline_sst not defined")

try:
    print("target_sst:", target_sst.shape)
except:
    print("target_sst not defined")

try:
    print("sea_cells:", sea_cells.shape)
except:
    print("sea_cells not defined")
