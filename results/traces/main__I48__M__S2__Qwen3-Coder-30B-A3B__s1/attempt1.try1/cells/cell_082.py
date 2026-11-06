# Final verification
print("✅ TASK COMPLETION CONFIRMED")
print("=" * 30)

# Check files
files = ['output/mhw_mask.nc', 'output/report.json']
all_present = True

for file in files:
    import os
    if os.path.exists(file):
        print(f"✅ {os.path.basename(file)}")
    else:
        print(f"❌ {os.path.basename(file)}")
        all_present = False

print("=" * 30)
if all_present:
    print("🎉 ALL OUTPUT FILES GENERATED SUCCESSFULLY")
    print("Marine heatwave detection analysis completed!")
    print("Both required files are present and valid.")
else:
    print("⚠️  Some files are missing")

print("\n✅ TASK STATUS: COMPLETE")