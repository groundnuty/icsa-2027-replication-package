import os, json
print("CWD:", os.getcwd())
print("work exists:", os.path.isdir('/work'))
os.makedirs('output', exist_ok=True)
print("made", os.path.abspath('output'))
