exec(open('/work/pipeline.py').read())
for i in range(1, 6):
    run_batch(i*800, 800, str(i))
