import fsspec
fs = fsspec.filesystem('onedata')
try:
    print("root:", fs.ls('/'))
except Exception as e:
    print("ls / failed:", repr(e))
# try to stat the file
p = "icsa2027_data_20261101T090944Z/s2z/sst_s2.nc"
try:
    print("info:", fs.info(p))
except Exception as e:
    print("info failed:", repr(e))
    try:
        print("info with slash:", fs.info("/" + p))
    except Exception as e2:
        print("info2 failed:", repr(e2))
