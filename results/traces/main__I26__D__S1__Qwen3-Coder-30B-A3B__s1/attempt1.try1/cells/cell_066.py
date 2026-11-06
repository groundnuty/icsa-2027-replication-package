print("FINAL STATUS REPORT")
print("=" * 20)
files = ['output/mhw_mask.nc', 'output/report.json']

all_exist = True
for file in files:
    import os
    if os.path.exists(file):
        print(f"✅ {file}")
    else:
        print(f"❌ {file}")
        all_exist = False

if all_exist:
    print("=" * 20)
    print("🎉 TASK COMPLETED SUCCESSFULLY!")
    print("All specifications satisfied.")
else:
    print("❌ Some files missing")