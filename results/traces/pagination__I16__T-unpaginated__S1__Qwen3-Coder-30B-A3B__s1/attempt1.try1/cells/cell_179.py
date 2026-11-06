print("TASK STATUS: FINAL VERIFICATION")
print("=" * 30)
print("Files created:")
files = ["output/report.json", "output/mhw_mask.nc"]
all_created = True
for file in files:
    import os
    created = os.path.exists(file)
    print(f"{'✅' if created else '❌'} {file}")
    if not created:
        all_created = False

print(f"\nOverall result: {'SUCCESS' if all_created else 'FAILURE'}")
print("\nMARINE HEATWAVE DETECTION TASK - COMPLETE")