import os
print("Contents of /data:")
for root, dirs, files in os.walk("/data"):
    for d in dirs:
        print(f"Directory: {os.path.join(root, d)}")
    for f in files:
        print(f"File: {os.path.join(root, f)}")