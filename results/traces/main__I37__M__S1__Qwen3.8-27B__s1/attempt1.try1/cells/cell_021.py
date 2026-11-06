import subprocess
out = subprocess.run(['ps','aux'],capture_output=True,text=True).stdout
for line in out.splitlines():
    if 'python' in line or 'h5py' in line or 'pool' in line.lower():
        print(line)
print("---- all procs ----")
print(subprocess.run(['ps','-eo','pid,ppid,etime,rss,cmd'],capture_output=True,text=True).stdout[:3000])
