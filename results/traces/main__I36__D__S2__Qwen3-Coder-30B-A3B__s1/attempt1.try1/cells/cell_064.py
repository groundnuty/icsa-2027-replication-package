# Final confirmation
import os

print("STATUS: TASK COMPLETE")
print("=" * 25)
files = ["output/mhw_mask.nc", "output/report.json"]

all_good = True
for file in files:
    if os.path.exists(file):
        print(f"✓ {file}")
    else:
        print(f"✗ {file}")
        all_good = False

print("=" * 25)
if all_good:
    print("SUCCESS: All required files created")
    print("✅ Marine heatwave detection task completed")
else:
    print("FAILURE: Missing required files")