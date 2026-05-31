#!/usr/bin/env bash
#
# Configure the build environment for Ubuntu 22.04 with GCC/G++ 14.
#
# IMPORTANT: this script must be *sourced*, not executed, otherwise the
# virtualenv activation and the CC/CXX exports only affect a throwaway
# subshell and vanish:
#
#     source config_ubuntu22.sh
#     # or
#     . config_ubuntu22.sh

# Detect whether we are being sourced. If executed directly, warn and bail
# out so the user does not silently get a no-op.
if [ "${BASH_SOURCE[0]}" = "${0}" ]; then
    echo "ERROR: this script must be sourced, not executed." >&2
    echo "       Run:  source ${0}" >&2
    exit 1
fi

# Resolve the directory of this script so .venv is found regardless of the
# current working directory.
_config_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ ! -f "${_config_dir}/.venv/bin/activate" ]; then
    echo "ERROR: ${_config_dir}/.venv/bin/activate not found." >&2
    echo "       Create the virtualenv first, e.g.:  python3 -m venv .venv" >&2
    unset _config_dir
    return 1
fi

source "${_config_dir}/.venv/bin/activate"
export CC=gcc-14
export CXX=g++-14

echo "Environment configured:"
echo "  venv : ${VIRTUAL_ENV}"
echo "  CC   : ${CC}"
echo "  CXX  : ${CXX}"

unset _config_dir