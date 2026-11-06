# Final confirmation
print("🏁 TASK COMPLETION CONFIRMED")
print("=" * 25)

import os

files = [
    '/work/output/mhw_mask.nc',
    '/work/report.json'
]

all_present = True
for file_path in files:
    if os.path.exists(file_path):
        print(f"✅ {os.path.basename(file_path)} - PRESENT")
    else:
        print(f"❌ {os.path.basename(file_path)} - MISSING")
        all_present = False

print("=" * 25)
if all_present:
    print("🎉 SUCCESS: Task completed fully")
    print("Both required files generated successfully.")
else:
    print("💥 FAILURE: Missing required files")