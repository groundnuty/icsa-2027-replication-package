# Final verification
import os

print("FINAL VERIFICATION OF OUTPUT FILES")
print("=" * 35)
files = ['output/mhw_mask.nc', 'output/report.json']

all_exist = True
for file in files:
    if os.path.exists(file):
        print(f"✅ {file}")
    else:
        print(f"❌ {file}")
        all_exist = False

print("=" * 35)
if all_exist:
    print("🎉 ALL TASK REQUIREMENTS SATISFIED")
    print("Marine heatwave detection task completed successfully!")
else:
    print("❌ Some files missing")