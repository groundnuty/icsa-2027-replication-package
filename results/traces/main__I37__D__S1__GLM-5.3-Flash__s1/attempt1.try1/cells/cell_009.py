import inspect
import onedatarestfsspec.core as core
# find the real (unwrapped) ls implementation
names = [n for n in dir(core.OnedataFileSystem) if 'ls' in n.lower()]
print(names)
for n in names:
    f = getattr(core.OnedataFileSystem, n, None)
    try:
        print(n, "->", inspect.unwrap(f).__qualname__)
    except Exception as e:
        print(n, "err", e)
