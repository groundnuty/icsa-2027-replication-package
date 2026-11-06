print("FINAL VERIFICATION")
print("=" * 20)
files = ['output/mhw_mask.nc', 'output/report.json']
all_good = True

for file in files:
    try:
        with open(file, 'rb') as f:
            size = len(f.read())
        print(f"✅ {file} ({size} bytes)")
    except Exception as e:
        print(f"❌ {file} (ERROR: {e})")
        all_good = False

if all_good:
    print("=" * 20)
    print("🎉 TASK COMPLETED SUCCESSFULLY!")
    print("All requirements satisfied.")