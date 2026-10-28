#!/bin/sh
set -eu

mkdir -p /var/data/chroma_db /var/data/uploads /var/data/library /var/data/huggingface
chown autosaarthi:autosaarthi /var/data /var/data/chroma_db /var/data/uploads /var/data/library /var/data/huggingface
exec gosu autosaarthi "$@"
