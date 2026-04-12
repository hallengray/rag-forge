#!/usr/bin/env bash
# Check whether RAG-Forge package names are available on npm and PyPI.
# Run before the first publish.

set -e

echo "Checking npm name availability..."
echo ""

check_npm() {
    local name="$1"
    if npm view "$name" version &>/dev/null; then
        echo "  TAKEN: $name"
        return 1
    else
        echo "  AVAILABLE: $name"
        return 0
    fi
}

check_pypi() {
    local name="$1"
    if curl -sf "https://pypi.org/pypi/$name/json" &>/dev/null; then
        echo "  TAKEN: $name"
        return 1
    else
        echo "  AVAILABLE: $name"
        return 0
    fi
}

echo "npm packages:"
check_npm "rag-forge" || true
check_npm "@rag-forge/mcp" || true
check_npm "@rag-forge/shared" || true

echo ""
echo "PyPI packages:"
check_pypi "rag-forge-core" || true
check_pypi "rag-forge-evaluator" || true
check_pypi "rag-forge-observability" || true

echo ""
echo "Done. If any names are TAKEN, you need to either:"
echo "  1. Use a different scope (e.g., @hallengray/rag-forge)"
echo "  2. Use a different name suffix"
echo "  3. Contact npm/PyPI support if you believe they should be available"
