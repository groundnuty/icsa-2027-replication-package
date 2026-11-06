import os, tempfile
for p in ['/tmp', '~', os.getcwd(), '.', './output', '/data', '/workspace']:
    try:
        os.makedirs(p, exist_ok=True)
        probe = os.path.join(p, 'probe.txt')
        with open(probe, 'w') as fh:
            fh.write('x')
        print("WRITABLE:", p)
        os.remove(probe)
    except Exception as e:
        print("no:", p, type(e).__name__, e)
print("cwd:", os.getcwd())
