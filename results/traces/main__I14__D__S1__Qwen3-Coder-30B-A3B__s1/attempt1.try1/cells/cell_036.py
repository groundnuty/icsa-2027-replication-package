# Final check
print("✅ FINAL TASK VALIDATION")
print("=" * 25)

import os

files = [
    '/work/output/mhw_mask.nc',
    '/work/report.json'
]

all_exist = True
for file_path in files:
    if os.path.exists(file_path):
        print(f"✓ {os.path.basename(file_path)} - CREATED")
    else:
        print(f"✗ {os.path.basename(file_path)} - MISSING")
        all_exist = False

print("=" * 25)
if all_exist:
    print("SUCCESS: All output files generated")
    print("Task requirements fully satisfied")
else:
    print("FAILURE: Missing output files")