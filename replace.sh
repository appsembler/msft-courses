#!/usr/bin/env bash
set -e
set -x
set -o pipefail


VIA_CURL=""
IMPORTER="$PWD/replacer.py"
BASE_URL="https://raw.githubusercontent.com/appsembler/msft-courses/master"


if [ "$0" == "bash" ]; then
    if [ -z "$1" ]; then
        VIA_CURL="true"
        IMPORTER=$(mktemp /tmp/abc-script.XXXXXXXX)
        curl "$BASE_URL/replacer.py" | tee "$REPLACER"
        chmod a+wrx "$REPLACER"
    fi
fi


python "$REPLACER"
