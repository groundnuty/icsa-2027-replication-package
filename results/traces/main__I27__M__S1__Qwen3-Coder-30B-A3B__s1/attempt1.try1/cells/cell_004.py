import os

# Let's find the right directory structure
print("Checking directories under /data:")
for root, dirs, files in os.walk("/data"):
    if "s1z" in root or "s2z" in root:
        print(f"Found: {root}")
        # Show first few files
        sample_files = files[:5] if len(files) > 5 else files
        for f in sample_files:
            print(f"  {f}")
        print()