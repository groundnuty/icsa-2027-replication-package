
import os, shutil
print("work usage:", shutil.disk_usage('/work'))
files = os.listdir('/work/files')
print("local files:", len(files))
tot = sum(os.path.getsize('/work/files/' + f) for f in files)
print("local total MB:", tot/1e6)
import subprocess
print(subprocess.run(['df','-h'], capture_output=True, text=True).stdout)
print(subprocess.run(['mount'], capture_output=True, text=True).stdout[:2000])
