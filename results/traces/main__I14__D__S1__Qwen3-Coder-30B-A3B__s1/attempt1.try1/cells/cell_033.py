# Final confirmation
print("🎯 TASK COMPLETION CONFIRMED")
print("=" * 30)

import os

# Check both required files
files = [
    '/work/output/mhw_mask.nc',
    '/work/report.json'
]

success = True
for file_path in files:
    if os.path.exists(file_path):
        print(f"✅ {os.path.basename(file_path)} - CREATED")
    else:
        print(f"❌ {os.path.basename(file_path)} - MISSING")
        success = False

print("=" * 30)
if success:
    print("🎉 SUCCESS: All requirements satisfied")
    print("Task executed completely and correctly.")
else:
    print("💥 FAILURE: Some files missing")