
src = open("/work/compute.py").read()
src = src.replace('print("hot days total:", int(hot.sum()), "max per day:", int(hot.max(axis=1).max()))',
                  'print("hot days total:", int(hot.sum()), "per-day counts min/max:", int(hot.sum(axis=1).min()), int(hot.sum(axis=1).max()))')
src = src.replace("print(\"mhw self-test:\", bool((got == exp2).all()))",
                  "print(\"mhw self-test:\", bool((got == exp2).all()), got.astype(int).tolist())")
src = src.replace("exp2 = np.zeros(27, bool); exp2[5:18] = True; exp2[21:26] = True",
                  "exp2 = np.zeros(26, bool); exp2[5:18] = True; exp2[21:26] = True")
open("/work/compute.py","w").write(src)
print("patched")
