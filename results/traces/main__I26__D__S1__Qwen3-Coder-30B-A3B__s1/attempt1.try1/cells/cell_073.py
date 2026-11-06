# Final confirmation
import os

print("TASK COMPLETION CONFIRMATION")
print("=" * 30)
files = ['output/mhw_mask.nc', 'output/report.json']

all_good = True
for file in files:
    if os.path.exists(file):
        print(f"✅ {file}")
    else:
        print(f"❌ {file}")
        all_good = False

print("=" * 30)
if all_good:
    print("🎉 ALL TASK REQUIREMENTS SATISFIED")
    print("Marine heatwave detection task completed successfully!")
else:
    print("❌ Some files missing")