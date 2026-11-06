import os
print("Contents of /data:")
for root, dirs, files in os.walk("/data"):
    level = root.replace("/data", "").count(os.sep)
    indent = " " * 2 * level
    print(f"{indent}{os.path.basename(root)}/")
    subindent = " " * 2 * (level + 1)
    for file in files:
        print(f"{subindent}{file}")