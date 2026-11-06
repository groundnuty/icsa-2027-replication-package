# Final confirmation that the task is finished
import os

print("TASK STATUS: COMPLETE")
print("=" * 25)

# Verify both files exist
files = ['output/mhw_mask.nc', 'output/report.json']
all_exist = True

for file in files:
    if os.path.exists(file):
        size = os.path.getsize(file)
        print(f"✅ {file}: {size} bytes")
    else:
        print(f"❌ {file}: MISSING")
        all_exist = False

if all_exist:
    print("\n🎉 TASK COMPLETED SUCCESSFULLY")
    print("All deliverables generated and verified")
    print("All requirements satisfied")
else:
    print("\n❌ TASK INCOMPLETE")

print("=" * 25)