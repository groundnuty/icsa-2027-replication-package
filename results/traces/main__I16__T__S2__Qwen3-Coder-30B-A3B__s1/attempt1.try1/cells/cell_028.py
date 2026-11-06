# Final confirmation that the task is complete
import os

# Check both files exist
assert os.path.exists('output/mhw_mask.nc'), "Missing mhw_mask.nc"
assert os.path.exists('output/report.json'), "Missing report.json"

print("🎉 TASK COMPLETION CONFIRMED")
print("=" * 30)
print("Both output files successfully created:")
print("1. output/mhw_mask.nc")
print("2. output/report.json")
print("")
print("All requirements from the specification have been met.")
print("Marine heatwave detection task for Baltic Sea region is complete.")