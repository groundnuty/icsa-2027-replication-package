# Final confirmation that both files exist
import os

print("📋 FINAL VERIFICATION COMPLETE")
print("=" * 30)

files = [
    '/work/output/mhw_mask.nc',
    '/work/report.json'
]

all_exist = True
for file_path in files:
    if os.path.exists(file_path):
        print(f"✅ {os.path.basename(file_path)} - CREATED")
    else:
        print(f"❌ {os.path.basename(file_path)} - MISSING")
        all_exist = False

print("=" * 30)
if all_exist:
    print("🎉 ALL FILES SUCCESSFULLY GENERATED")
    print("Task completion verified.")
else:
    print("💥 SOME FILES ARE MISSING")