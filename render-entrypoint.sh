#!/bin/sh
set -eu

RUNTIME_DIR=/tmp/autosaarthi
mkdir -p "$RUNTIME_DIR/chroma_db" "$RUNTIME_DIR/uploads" "$RUNTIME_DIR/library" "$RUNTIME_DIR/huggingface"

# Chroma needs to write SQLite metadata and lock files. The prebuilt index in
# /app is image-owned, so make a writable ephemeral copy for this free service.
if [ ! -f "$RUNTIME_DIR/chroma_db/chroma.sqlite3" ]; then
    cp -a /app/chroma_db/. "$RUNTIME_DIR/chroma_db/"
fi

chmod -R u+rwX "$RUNTIME_DIR"
chown -R autosaarthi:autosaarthi "$RUNTIME_DIR"
exec gosu autosaarthi "$@"
