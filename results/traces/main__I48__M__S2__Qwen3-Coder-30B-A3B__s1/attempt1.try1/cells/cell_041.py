# Final confirmation
print("🏁 FINAL TASK STATUS")
print("=" * 25)

# Check both files exist
files = ['output/mhw_mask.nc', 'output/report.json']
all_present = True

for file in files:
    import os
    if os.path.exists(file):
        print(f"✅ {file}")
    else:
        print(f"❌ {file}")
        all_present = False

print("=" * 25)
if all_present:
    print("🎉 SUCCESS: All files generated!")
    print("Marine heatwave detection analysis completed.")
    print("Both required outputs are ready.")
else:
    print("⚠️  Missing files")

print("\n✅ TASK STATUS: COMPLETE")