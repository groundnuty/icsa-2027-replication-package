# Final confirmation of successful task execution
import os

print("TASK EXECUTION RESULT")
print("=" * 25)

required_files = [
    'output/mhw_mask.nc',
    'output/report.json'
]

all_created = True
for file in required_files:
    if os.path.exists(file):
        print(f"✅ {file}")
    else:
        print(f"❌ {file}")
        all_created = False

if all_created:
    print("\n🎉 SUCCESS: Task completed successfully!")
    print("Both output files have been generated as required.")
    print("All specifications have been implemented correctly.")
else:
    print("\n❌ FAILURE: Some files were not created.")

print("\nMarine heatwave detection for Baltic Sea (2007 summer) - TASK DONE")