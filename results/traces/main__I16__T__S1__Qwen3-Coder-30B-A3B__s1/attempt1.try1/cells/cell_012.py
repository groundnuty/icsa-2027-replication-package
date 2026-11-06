# Final status check
import os

print("Final Status Check:")
print("-" * 30)

files_exist = []
required_files = ["output/report.json"]

for file in required_files:
    exists = os.path.exists(file)
    print(f"{file}: {'✓ EXISTS' if exists else '✗ MISSING'}")
    if exists:
        files_exist.append(file)

print(f"\nStatus: {'COMPLETE' if len(files_exist) == len(required_files) else 'INCOMPLETE'}")