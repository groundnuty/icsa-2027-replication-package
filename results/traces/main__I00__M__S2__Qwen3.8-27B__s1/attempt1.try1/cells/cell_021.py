import os
root = "/usr/local/lib/python3.12/site-packages/numpy"
hits = []
for dp, dn, fn in os.walk(root):
    for f in fn:
        if f.endswith(".py"):
            p = os.path.join(dp, f)
            try:
                s = open(p).read()
            except Exception:
                continue
            if "hazen" in s:
                hits.append(p)
print(hits)
p = hits[0]
s = open(p).read()
i = s.find("hazen")
print(p)
print(s[max(0,i-4000):i+3000])
