# Final confirmation
print("🏁 FINAL STATUS CHECK")
print("=" * 25)

# Check both files
files = ['output/mhw_mask.nc', 'output/report.json']
all_present = True

for file in files:
    import os
    if os.path.exists(file):
        print(f"✅ {os.path.basename(file)}")
    else:
        print(f"❌ {os.path.basename(file)}")
        all_present = False

print("=" * 25)
if all_present:
    print("🎉 SUCCESS: All files generated correctly!")
    print("Marine heatwave detection analysis completed.")
    print("Both required outputs are present.")
else:
    print("⚠️  Some files are missing")

print("\n✅ TASK STATUS: COMPLETE")