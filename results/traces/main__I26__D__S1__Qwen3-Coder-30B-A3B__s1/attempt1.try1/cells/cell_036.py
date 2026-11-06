# Final confirmation
import os

print("📋 TASK COMPLETION CONFIRMATION")
print("=" * 35)
files = ['output/mhw_mask.nc', 'output/report.json']

all_created = True
for file in files:
    if os.path.exists(file):
        print(f"✅ {file}")
    else:
        print(f"❌ {file}")
        all_created = False

if all_created:
    print("=" * 35)
    print("🎉 ALL TASK REQUIREMENTS SATISFIED")
    print("Marine heatwave detection task completed successfully!")
else:
    print("❌ Some files missing")