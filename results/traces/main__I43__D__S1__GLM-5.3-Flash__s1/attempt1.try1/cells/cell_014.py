import os
print(os.listdir('/work'))
for d in ['test','dl','dl2','dl3']:
    p = os.path.join('/work', d)
    if os.path.isdir(p): print(d, len(os.listdir(p)))
import shutil
print(shutil.disk_usage('/work'))
