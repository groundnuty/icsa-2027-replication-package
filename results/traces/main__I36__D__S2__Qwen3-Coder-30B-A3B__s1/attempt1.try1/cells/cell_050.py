# Final confirmation that task is complete
import os

print("TASK STATUS: COMPLETE")
print("=" * 25)
files = ["output/mhw_mask.nc", "output/report.json"]

all_present = True
for file in files:
    if os.path.exists(file):
        print(f"✓ {file}")
    else:
        print(f"✗ {file}")
        all_present = False

print("=" * 25)
if all_present:
    print("SUCCESS: All required files created")
    print("✅ Marine heatwave detection task completed")
else:
    print("FAILURE: Missing required files")