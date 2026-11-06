import os
for p in os.listdir('/proc'):
    if p.isdigit():
        try:
            c=open(f'/proc/{p}/cmdline','rb').read().replace(b'\0',b' ').decode()
            if 'fetch' in c: print(p,c)
        except Exception: pass