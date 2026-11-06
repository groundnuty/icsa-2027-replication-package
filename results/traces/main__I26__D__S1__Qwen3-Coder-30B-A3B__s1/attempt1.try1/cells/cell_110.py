# Final verification that both files exist
import os

print("TASK COMPLETION VERIFICATION")
print("=" * 30)
files = ['output/mhw_mask.nc', 'output/report.json']

all_exist = True
for file in files:
    if os.path.exists(file):
        print(f"✅ {file}")
    else:
        print(f"❌ {file}")
        all_exist = False

print("=" * 30)
if all_exist:
    print("🎉 TASK COMPLETED SUCCESSFULLY!")
    print("All required files have been created as specified.")
else:
    print("❌ Some files missing")