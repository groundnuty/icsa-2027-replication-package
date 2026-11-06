script = open("/tmp/mhw_work/extract.py").read()
old = """    base = []
    for y in range(1992, 2003):
        if dd == 1:
            if y-1 == 1991:
                base.append(rmap[(366, 1991)])
        elif dd == 2:
            if y-1 == 1991:
                base += [rmap[(366, 1991)], rmap[(1, 1991)]]
        elif dd <= 61:
            for e in range(dd-5, dd+5+1):
                if 1 <= e <= (366 if calendar.isleap(y-1) else 365):
                    base.append(rmap[(e, y-1)])
        for e in range(max(1, dd-5), min(366, dd+5)+1):
            if e <= (366 if calendar.isleap(y) else 365):
                base.append(rmap[(e, y)])
    win.append(sorted(set(base)))"""
new = """    base = []
    def valid_doy(e, yr):
        if yr == 60:  # placeholder to avoid flake; unused
            return False
        if e == 60:
            return calendar.isleap(yr)
        ndays = 366 if calendar.isleap(yr) else 365
        return 1 <= e <= ndays
    for y in range(1992, 2003):
        if dd == 1:
            if y-1 == 1991:
                base.append(rmap[(366, 1991)])
        elif dd == 2:
            if y-1 == 1991:
                base += [rmap[(366, 1991)], rmap[(1, 1991)]]
        elif dd <= 61:
            for e in range(dd-5, dd+5+1):
                if valid_doy(e, y-1):
                    base.append(rmap[(e, y-1)])
        for e in range(max(1, dd-5), min(366, dd+5)+1):
            if valid_doy(e, y):
                base.append(rmap[(e, y)])
    win.append(sorted(set(base)))"""
assert old in script
script = script.replace(old, new)
open("/tmp/mhw_work/extract.py", "w").write(script)
print("patched")
