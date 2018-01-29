#!/usr/bin/env bash
set -e
set -x
set -o pipefail


VIA_CURL=""
IMPORTER="$PWD/importer.py"
BASE_URL="https://appsembler.github.io/msft-courses/"
COURSES_DIR="$PWD"

if [ -d /edx/src ]; then
    EDXAPP_ENV=devstack_appsembler
else
    EDXAPP_ENV=aws_appsembler
fi

if [ "$0" == "bash" ]; then
    if [ -z "$1" ]; then
        VIA_CURL="true"
        IMPORTER="/tmp/importer.py"
        curl --progress-bar "$BASE_URL/importer.py" > $IMPORTER
    fi
fi


CMS_SHELL="sudo -u edxapp /edx/bin/python.edxapp /edx/bin/manage.edxapp lms --settings=$EDXAPP_ENV shell"
echo "__file__='$IMPORTER'; COURSES_DIR='$COURSES_DIR'; execfile(__file__);" | $CMS_SHELL
