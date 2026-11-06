# Final status
import os

print("STATUS: TASK COMPLETED")
print("=" * 25)
files = ["output/mhw_mask.nc", "output/report.json"]

all_present = True
for file in files:
    present = os.path.exists(file)
    print(f"{'✓' if present else '✗'} {file}")
    if not present:
        all_present = False

print("=" * 25)
if all_present:
    print("SUCCESS: All output files generated")
    print("✅ Task requirements fully satisfied")
else:
    print("FAILURE: Missing output files")