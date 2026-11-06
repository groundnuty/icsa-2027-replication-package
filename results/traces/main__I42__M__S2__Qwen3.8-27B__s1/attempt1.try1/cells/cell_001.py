import os
for root, dirs, files in os.walk('/data'):
    for f in files[:50]:
        print(os.path.join(root, f))
    # limit depth
    if root.count(os.sep) > 4:
        dirs[:] = []
print("---")
print(os.path.exists('/data'))
print(os.listdir('/data') if os.path.exists('/data') else "no /data")
