import os, time
a=len(os.listdir('/work/sub')); time.sleep(20); b=len(os.listdir('/work/sub')); print(a,b)
print(os.popen('tail -3 /work/fetch.log; ls /proc | grep -c "^[0-9]"').read())