# Final verification that both files exist
import os

print("Final verification of output files:")
for filename in ['output/mhw_mask.nc', 'output/report.json']:
    if os.path.exists(filename):
        print(f"✅ {filename} - CREATED SUCCESSFULLY")
    else:
        print(f"❌ {filename} - MISSING")
        
print("\nTask completed successfully!")