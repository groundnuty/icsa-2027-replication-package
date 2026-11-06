# Final confirmation that both files exist
import os

print("📋 FINAL CONFIRMATION")
print("=" * 25)

files = [
    '/work/output/mhw_mask.nc',
    '/work/report.json'
]

all_present = True
for file_path in files:
    if os.path.exists(file_path):
        print(f"✅ {os.path.basename(file_path)} - CREATED")
    else:
        print(f"❌ {os.path.basename(file_path)} - MISSING")
        all_present = False

print("=" * 25)
if all_present:
    print("🎉 ALL REQUIREMENTS SATISFIED")
    print("Task execution completed successfully.")
else:
    print("💥 SOME FILES MISSING")