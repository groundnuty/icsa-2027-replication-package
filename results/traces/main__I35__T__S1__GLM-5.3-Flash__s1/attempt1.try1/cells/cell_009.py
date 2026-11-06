import os, tempfile, pathlib
print('cwd:', os.getcwd())
print('home:', os.path.expanduser('~'))
print('tempdir:', tempfile.gettempdir())
for d in [tempfile.gettempdir(), os.path.expanduser('~'), os.getcwd(), '/tmp', '~', '~']:
    try:
        os.makedirs(d, exist_ok=True)
        p=os.path.join(d,'.wtest')
        with open(p,'w') as f: f.write('x')
        os.remove(p)
        print('WRITABLE:', d)
    except Exception as ex:
        print('not writable:', d, repr(ex)[:100])
