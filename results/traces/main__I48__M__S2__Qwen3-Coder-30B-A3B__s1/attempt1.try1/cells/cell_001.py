import os
print("Contents of /data:")
for root, dirs, files in os.walk("/data"):
    for file in files:
        print(os.path.join(root, file))
    for dir in dirs:
        print(os.path.join(root, dir))