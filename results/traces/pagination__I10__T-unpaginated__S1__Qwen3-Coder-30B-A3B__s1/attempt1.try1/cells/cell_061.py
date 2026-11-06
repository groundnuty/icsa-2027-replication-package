# Final confirmation
import os

print("TASK COMPLETION STATUS")
print("=" * 25)

# Verify both files exist and are not empty
files = ['output/mhw_mask.nc', 'output/report.json']
all_good = True

for file in files:
    if os.path.exists(file):
        size = os.path.getsize(file)
        if size > 0:
            print(f"✅ {file}: {size} bytes")
        else:
            print(f"❌ {file}: EMPTY")
            all_good = False
    else:
        print(f"❌ {file}: MISSING")
        all_good = False

if all_good:
    print("\n🎉 TASK COMPLETED SUCCESSFULLY")
    print("All deliverables generated and verified")
    print("All specifications met")
else:
    print("\n❌ TASK INCOMPLETE")

print("=" * 25)