import pickle,numpy as np,pandas as pd
dates,R=pickle.load(open('/tmp/r.pkl','rb'))
la,lo=R[0][1],R[0][2];print(la[:4],la[-3:],lo[:4],lo[-3:])