import os, re
# memory info
mi = open('/proc/meminfo').read()
print("\n".join(l for l in mi.splitlines() if any(k in l for k in ['MemTotal','MemFree','MemAvailable','Cached'])))
# python processes
for pid in os.listdir('/proc'):
    if pid.isdigit():
        try:
            with open(f'/proc/{pid}/cmdline','rb') as f:
                cmd = f.read().replace(b'\0', b' ').decode()[:120]
            with open(f'/proc/{pid}/status') as f:
                st = [l for l in f if l.startswith(('VmRSS','VmSize','State','Name'))]
            if 'python' in cmd or 'dl.py' in cmd:
                print(pid, cmd, st)
        except Exception:
            pass