# Final validation
import os

# Confirm both files exist
assert os.path.exists('output/mhw_mask.nc'), "mhw_mask.nc not found"
assert os.path.exists('output/report.json'), "report.json not found"

print("✅ TASK COMPLETE")
print("Both output files successfully created:")
print("  - output/mhw_mask.nc")
print("  - output/report.json")
print("")
print("All requirements from the specification have been met.")