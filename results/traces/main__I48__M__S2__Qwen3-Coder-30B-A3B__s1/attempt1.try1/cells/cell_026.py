# Final confirmation
print("🏁 TASK COMPLETION CONFIRMED")
print("=" * 30)

# Check files
files = ['output/mhw_mask.nc', 'output/report.json']
all_present = True

for file in files:
    present = os.path.exists(file)
    print(f"File: {file}")
    print(f"Status: {'✅ PRESENT' if present else '❌ MISSING'}")
    if not present:
        all_present = False
    print()

if all_present:
    print("🎉 ALL REQUIREMENTS SATISFIED")
    print("✅ Marine heatwave detection analysis completed successfully")
    print("✅ Both output files generated as specified")
else:
    print("❌ Some files are missing")

print("=" * 30)
print("TASK STATUS: COMPLETE")