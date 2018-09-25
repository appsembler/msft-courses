#!/usr/bin/env bash
set -e
set -x
set -o pipefail


REPLACER="$PWD/replacer.py"
BASE_URL="https://raw.githubusercontent.com/appsembler/msft-courses/master"


if [ "$0" == "bash" ]; then
    if [ -z "$1" ]; then
        REPLACER=$(mktemp /tmp/abc-script.XXXXXXXX)
        curl "$BASE_URL/replacer.py" | tee "$REPLACER"
        chmod a+wrx "$REPLACER"
    fi
fi


python "$REPLACER"
