# Replication package: one command checks the files and regenerates the analysis tables of the fixed snapshot.
#   make check     verify checksums.sha256, then regenerate every table and compare it with the shipped one
#   make verify    checksums.sha256 only (standard library, no dependencies)
#   make tables    regenerate the tables into build/tables without comparing
#   make equality  the knowledge-plane equality table, from results/knowledge
#   make clean     remove build/

PY ?= uv run python

.PHONY: check verify tables equality clean

check: verify
	rm -rf build/tables
	$(PY) reproduce/regenerate.py --out build/tables --check

verify:
	python3 reproduce/checksums.py

tables:
	rm -rf build/tables
	$(PY) reproduce/regenerate.py --out build/tables

equality:
	mkdir -p build
	python3 reproduce/equality_table.py results/knowledge > build/equality_table.md
	@echo "wrote build/equality_table.md"

clean:
	rm -rf build
