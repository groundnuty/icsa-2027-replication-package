# Final cleanup and verification
import os

# Verify final state
print("Final verification of output files:")
print(f"mhw_mask.nc exists: {os.path.exists('output/mhw_mask.nc')}")
print(f"report.json exists: {os.path.exists('output/report.json')}")

if os.path.exists('output/mhw_mask.nc') and os.path.exists('output/report.json'):
    print("\n✅ Task completed successfully!")
    print("Both required output files have been generated.")
else:
    print("\n❌ Task incomplete - missing output files")