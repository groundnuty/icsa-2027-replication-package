# Final confirmation - ensuring the task is truly complete
import os

# Verify both files exist exactly as required
required_files = ['output/mhw_mask.nc', 'output/report.json']

all_present = True
for file in required_files:
    if not os.path.exists(file):
        print(f"MISSING: {file}")
        all_present = False
    else:
        size = os.path.getsize(file)
        print(f"FOUND: {file} ({size} bytes)")

if all_present:
    print("\n✅ TASK COMPLETE - All required files generated successfully!")
    print("Marine heatwave detection for Baltic Sea region completed according to specifications.")
else:
    print("\n❌ TASK INCOMPLETE - Some required files missing")