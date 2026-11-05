"""Blind code inspection of runs (#76, rubric amendment 11): packets, queue, coders, decision rule, report.

    packet.py   one run -> one sanitised, cue-scanned text (rubric §3)
    queue.py    sets R, C and K-test in one seeded order; the key file stays outside the packets
    prompt.py   the coder prompt (rubric §4 only) and its hash
    answer.py   the structured answer's schema and validation
    compare.py  a coder's extraction against the required extent -> its verdict (§5)
    decide.py   the decision rule (§5): only an instrument `unknown` is ever resolved
"""
