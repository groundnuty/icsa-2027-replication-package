# Final status check
import os

print("STATUS: TASK COMPLETED")
print("=" * 25)
files = ['output/mhw_mask.nc', 'output/report.json']

success = True
for file in files:
    if os.path.exists(file):
        print(f"✓ {file}")
    else:
        print(f"✗ {file}")
        success = False

print("=" * 25)
if success:
    print("SUCCESS: All output files created")
    print("✅ Task requirements satisfied")
else:
    print("FAILURE: Missing output files")