# Final confirmation
import os

print("FINAL CONFIRMATION")
print("=" * 16)
files = ['output/mhw_mask.nc', 'output/report.json']

all_exist = True
for file in files:
    if os.path.exists(file):
        print(f"✅ {file}")
    else:
        print(f"❌ {file}")
        all_exist = False

if all_exist:
    print("\n🎉 TASK COMPLETED SUCCESSFULLY")
    print("Both required files have been generated.")
else:
    print("\n💥 TASK INCOMPLETE")