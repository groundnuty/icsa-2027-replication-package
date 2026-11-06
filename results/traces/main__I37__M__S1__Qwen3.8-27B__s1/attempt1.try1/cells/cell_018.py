import os
for p in ('/tmp/mhw/sst_ext.npy','/tmp/mhw/sst_tgt.npy'):
    st = os.stat(p)
    print(p, "size:", st.st_size)
    with open(p,'rb') as f:
        head = f.read(64)
    print("head:", head[:32].hex())
# expected size: header ~128B + 4028*60*60*4 = 57,987,840
print("expected ext data bytes:", 4028*60*60*4)
print("expected tgt data bytes:", 92*60*60*4)
