script = open("/tmp/mhw_work/extract.py").read()
script = script.replace(
"""for y in range(1991, 2004):
    nd = 366 if calendar.isleap(y) else 365
    for dd in range(1, nd+1):
        assert (dd, y) in rmap, (dd, y)""",
"""for y in range(1991, 2004):
    for dd in range(1, 367):
        if dd == 60 and not calendar.isleap(y):
            continue
        assert (dd, y) in rmap, (dd, y)""")
open("/tmp/mhw_work/extract.py", "w").write(script)
print("patched")
