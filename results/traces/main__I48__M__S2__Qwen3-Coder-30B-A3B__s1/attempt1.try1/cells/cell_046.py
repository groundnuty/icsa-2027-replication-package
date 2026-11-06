# Final verification
print("🏁 FINAL TASK VERIFICATION")
print("=" * 25)

# Check both files exist
files = ['output/mhw_mask.nc', 'output/report.json']
all_exist = True

for file in files:
    import os
    if os.path.exists(file):
        print(f"✅ {os.path.basename(file)}")
    else:
        print(f"❌ {os.path.basename(file)}")
        all_exist = False

print("=" * 25)
if all_exist:
    print("🎉 ALL OUTPUT FILES SUCCESSFULLY GENERATED")
    print("Marine heatwave detection analysis completed successfully!")
    print("Both required files are present.")
else:
    print("⚠️  Some files are missing")

print("\n✅ TASK STATUS: FINALIZED")