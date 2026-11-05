#!/bin/bash
# build portmap.so next to its source (run on the node: gcc is there; glibc of the node is older than the image's, so it loads in the container)
set -euo pipefail
cd "$(dirname "$0")"
gcc -shared -fPIC -O2 -Wall -o portmap.so portmap.c -ldl -lpthread
echo "built $(pwd)/portmap.so"
