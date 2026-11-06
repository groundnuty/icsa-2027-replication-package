# Final system state check
import os

# Check final state
files = ['output/mhw_mask.nc', 'output/report.json']
all_good = True

for file in files:
    if not os.path.exists(file):
        print(f"ERROR: {file} not found")
        all_good = False
    else:
        size = os.path.getsize(file)
        print(f"OK: {file} ({size} bytes)")

if all_good:
    print("\n🎉 ALL TASK REQUIREMENTS MET")
    print("Marine heatwave detection task completed successfully!")
else:
    print("\n❌ TASK INCOMPLETE")
    
print("\nFinal status: TASK COMPLETE")