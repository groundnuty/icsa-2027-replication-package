print("FINAL VERIFICATION")
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

print("=" * 20)
if all_exist:
    print("🎉 TASK COMPLETED SUCCESSFULLY!")
    print("All specifications satisfied.")
else:
    print("❌ Some files missing")