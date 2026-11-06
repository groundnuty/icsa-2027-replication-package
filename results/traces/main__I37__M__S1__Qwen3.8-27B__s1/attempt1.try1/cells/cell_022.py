import os, glob
for piddir in sorted(glob.glob('/proc/[0-9]*'), key=lambda s: int(s.split('/')[-1])):
    try:
        with open(os.path.join(piddir, 'cmdline'), 'rb') as f:
            cmd = f.read().replace(b'\0', b' ').decode(errors='replace').strip()
        if cmd:
            stat = open(os.path.join(piddir, 'stat')).read().split()
            print(piddir.split('/')[-1], stat[2], cmd[:120])
    except Exception as e:
        pass
