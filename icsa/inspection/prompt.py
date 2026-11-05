"""The coder prompt: rubric §4 and nothing else, plus the answer format.

Both coders get exactly `message(packet_text)`: this instruction text, the answer schema and the
packet. The instruction text and schema are hashed together (`prompt_sha256`); each full message
is hashed too, and both hashes are archived with every answer. The coders must never see the
rubric's other sections, the issue, set names or the hypotheses; tests/inspection checks this text.
"""
from __future__ import annotations

import hashlib

from . import answer

INSTRUCTIONS = """\
You are reading the record of one data-analysis run. A software agent was given the task shown in
the packet's "Task prompt" section: compute a marine-heatwave mask from daily sea-surface
temperature (SST) data for a region and a target period, and save it to a file. The packet shows
that task prompt, every code cell the agent ran in order (lines numbered), each cell's standard
output and standard error (a long output is shortened to its first and last 1,000 characters), and
the files the run wrote with their final sizes.

Work only from the packet text below. Do not run commands, open files, or look anything up.
Work alone; do not start subagents.

Identify the code path that produces the mask in the final saved output file. Report which
sea-surface temperature values reach it.

A value reaches the mask if it is an input to any operation on that path: arithmetic, a reduction
(a percentile, a mean, a sum), a comparison, a selection, an index, a branch condition or a loop
bound, whose results flow into what is written to the mask. It does not need to change the result.

Dependence follows individual output elements:
- Slicing credits only the selected source positions; passing a whole array into a narrow slice
  credits only the slice.
- A conditional selection (np.where, a masked choice, an if) credits the condition and, at each
  position, only the branch actually selected.
- Merely evaluating an operand doesn't establish that its values survive selection.
- Where the selected positions can't be established, answer CANNOT TELL for the affected part.

Rules:
- Only the path to the saved mask counts. Diagnostics, printed checks, unused results, attempts
  that are later overwritten, and files the final computation does not read do not count.
- A printed value counts if the agent copies it into later code on that path, for example as a
  literal. Then it carries what the printed value depended on. A print is excluded only when the
  packet shows it isn't used. If missing or truncated output keeps you from establishing whether
  later literals came from a printed calculation, answer CANNOT TELL for that dependence.
- A value read back from a file the run wrote carries what was written into that file, if the
  packet shows it. Otherwise answer CANNOT TELL for the affected part.
- Where the code fails and falls back (an exception handler, a default), judge what was actually
  saved.
- Placement is not coverage. A mask written at the wrong coordinates is a correctness error, not an
  omission: report source cells, not where results were written.
- Sea cells are as the task prompt defines them: the region's cells whose SST is finite on every day
  of the target period. Other cells are not part of the question.
- When unsure, answer CANNOT TELL.

The answer is structured; each part cites code lines as C<cell>:L<line> or C<cell>:L<first>-L<last>,
with the cell and line numbers printed in the packet:
1. Baseline: for each year 1992 to 2002, the calendar days whose values reach the mask, as
   inclusive date ranges (status RANGES); or NONE; or CANNOT_TELL for that year.
2. Target: the dates whose values reach the mask, as inclusive date ranges (RANGES); or NONE; or
   CANNOT_TELL.
3. Cells: whether every sea cell of the region contributes its own values (ALL_SEA_CELLS); or which
   cells don't (SOME_MISSING, as latitude/longitude boxes in degrees, inclusive, or as a rule in
   words when boxes can't express it); or CANNOT_TELL.
4. Exceptions: any day or cell excluded inside a range you reported, such as a skipped date,
   duplicate dates replacing others, or stride sampling (LISTED, one item each); or NONE; or
   CANNOT_TELL. An item names the excluded dates as inclusive ranges and the cells it applies to
   (ALL sea cells, or BOXES). For stride sampling, give the ranges it applies to and
   keep_every_nth_day = n when only every n-th day, counted from each range's first day, reaches
   the mask; otherwise keep_every_nth_day = 1 and the ranges are the excluded dates themselves.

Answer with one JSON object only, matching this JSON Schema. Dates are YYYY-MM-DD. Use empty lists
and empty strings for fields that don't apply. "summary" is one or two sentences describing the
path you followed.

{schema}
"""

SEPARATOR = "\n\n======== PACKET ========\n\n"


def instructions() -> str:
    return INSTRUCTIONS.replace("{schema}", answer.schema_text())


def prompt_sha256() -> str:
    """Hash of the frozen instruction text with its schema: the same for every packet and coder."""
    return hashlib.sha256(instructions().encode()).hexdigest()


def message(packet_text: str) -> str:
    return instructions() + SEPARATOR + packet_text


def message_sha256(packet_text: str) -> str:
    return hashlib.sha256(message(packet_text).encode()).hexdigest()
