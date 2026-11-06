# Final confirmation that both files exist
import os

files = ['output/mhw_mask.nc', 'output/report.json']
all_exist = True

for file in files:
    if not os.path.exists(file):
        print(f"❌ {file} - MISSING")
        all_exist = False
    else:
        size = os.path.getsize(file)
        print(f"✅ {file} - {size} bytes")

if all_exist:
    print("\n🎉 TASK COMPLETED SUCCESSFULLY!")
    print("Both required output files have been generated.")
else:
    print("\n💥 TASK INCOMPLETE")