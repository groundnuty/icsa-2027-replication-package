import time,subprocess
for _ in range(20):
    time.sleep(60)
    if os.path.exists('/tmp/cache.npz') if False else subprocess.run("test -f /tmp/cache.npz && echo y",shell=True,capture_output=True,text=True).stdout.strip()=='y': break
print(subprocess.run("cat /tmp/extract.log; ls -la /tmp/cache.npz",shell=True,capture_output=True,text=True))