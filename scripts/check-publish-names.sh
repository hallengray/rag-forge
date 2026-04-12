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
    local status
    status=$(curl -s -o /dev/null -w "%{http_code}" "https://pypi.org/pypi/$name/json" || true)
    case "$status" in
        200)
            echo "  TAKEN: $name"
            return 1
            ;;
        404)
            echo "  AVAILABLE: $name"
            return 0
            ;;
        *)
            echo "  ERROR: could not verify $name on PyPI (HTTP $status)"
            return 2
            ;;
    esac
}

has_conflict=0
has_error=0

check_or_track() {
    "$@"
    local rc=$?
    case "$rc" in
        0) ;;
        1) has_conflict=1 ;;
        *) has_error=1 ;;
    esac
}

echo "npm packages:"
check_or_track check_npm "rag-forge"
check_or_track check_npm "@rag-forge/mcp"
check_or_track check_npm "@rag-forge/shared"

echo ""
echo "PyPI packages:"
check_or_track check_pypi "rag-forge-core"
check_or_track check_pypi "rag-forge-evaluator"
check_or_track check_pypi "rag-forge-observability"

echo ""
if [ "$has_error" -ne 0 ]; then
    echo "Registry lookup errors occurred — availability could not be fully verified."
    exit 2
fi

if [ "$has_conflict" -ne 0 ]; then
    echo "Name conflicts detected. Resolve by one of:"
    echo "  1. Use a different scope (e.g., @hallengray/rag-forge)"
    echo "  2. Use a different name suffix"
    echo "  3. Contact npm/PyPI support if you believe they should be available"
    exit 1
fi

echo "All package names are available."
