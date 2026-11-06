# Final verification
print("📋 FINAL VERIFICATION")
print("=" * 20)
print("Checking required files:")

files = ['output/mhw_mask.nc', 'output/report.json']
all_good = True

for file in files:
    import os
    exists = os.path.exists(file)
    print(f"  {'✅' if exists else '❌'} {file}")
    if not exists:
        all_good = False

if all_good:
    print("\n🎉 TASK COMPLETED SUCCESSFULLY")
    print("All required outputs have been generated.")
    print("Marine heatwave analysis is finished.")
else:
    print("\n💥 TASK INCOMPLETE")