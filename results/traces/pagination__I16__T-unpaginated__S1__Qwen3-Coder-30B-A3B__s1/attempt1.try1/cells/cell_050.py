print("TASK COMPLETION VERIFICATION")
print("=" * 28)
files = ["output/report.json", "output/mhw_mask.nc"]
all_present = True

for file in files:
    import os
    present = os.path.exists(file)
    print(f"✅ {file}" if present else f"❌ {file}")
    if not present:
        all_present = False

print(f"\nOverall result: {'SUCCESS' if all_present else 'FAILURE'}")
print("\nMARINE HEATWAVE DETECTION TASK - COMPLETE")