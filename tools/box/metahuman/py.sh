#!/bin/bash
# Run a Python file (or - for stdin) inside the MetaHuman scratch editor through MCP 8006.
# Usage: py.sh <file.py | -> [max_chars]
exec env MI_MCP_URL=http://127.0.0.1:8006/mcp python3 /project/ue/metahuman/scripts/mi_mcp.py py "$@"
