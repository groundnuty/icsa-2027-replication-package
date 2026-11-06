"""Runs a script unchanged, dumping the stack every 20 s, so a probe that dies shows where it was."""
import faulthandler, runpy, sys
faulthandler.dump_traceback_later(20, repeat=True, file=sys.stderr)
script = sys.argv[1]; sys.argv = sys.argv[1:]
runpy.run_path(script, run_name="__main__")
