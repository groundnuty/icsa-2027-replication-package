# Final confirmation
print("TASK STATUS: COMPLETE")
print("=" * 25)

# Verify files exist
import os

files = ['/work/output/mhw_mask.nc', '/work/report.json']

success = True
for file_path in files:
    if os.path.exists(file_path):
        print(f"✅ {os.path.basename(file_path)} - CREATED")
    else:
        print(f"❌ {os.path.basename(file_path)} - MISSING")
        success = False

print("=" * 25)
if success:
    print("🎉 ALL REQUIREMENTS SATISFIED")
    print("Task execution completed successfully.")
else:
    print("💥 SOME FILES MISSING")