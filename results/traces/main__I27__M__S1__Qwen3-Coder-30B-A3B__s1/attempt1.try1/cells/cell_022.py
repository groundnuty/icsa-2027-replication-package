# Final confirmation
import os

# Check files exist
files = ['output/mhw_mask.nc', 'output/report.json']
all_exist = True

for file in files:
    if not os.path.exists(file):
        print(f"❌ Missing: {file}")
        all_exist = False
    else:
        print(f"✅ Found: {file}")

if all_exist:
    print("\n🎉 TASK COMPLETED SUCCESSFULLY")
    print("Both required output files have been generated.")
else:
    print("\n💥 TASK INCOMPLETE")