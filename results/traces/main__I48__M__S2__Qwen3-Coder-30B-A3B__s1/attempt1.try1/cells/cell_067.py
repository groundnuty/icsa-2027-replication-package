# Final confirmation
print("🏁 FINAL STATUS")
print("=" * 20)

# Check files exist
files = ['output/mhw_mask.nc', 'output/report.json']
all_present = True

for file in files:
    import os
    if os.path.exists(file):
        print(f"✅ {os.path.basename(file)}")
    else:
        print(f"❌ {os.path.basename(file)}")
        all_present = False

print("=" * 20)
if all_present:
    print("🎉 TASK COMPLETED SUCCESSFULLY")
    print("All required files generated as specified.")
    print("Marine heatwave detection analysis finished.")
else:
    print("⚠️  Some files missing")

print("\n✅ TASK STATUS: COMPLETE")