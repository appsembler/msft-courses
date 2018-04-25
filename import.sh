#!/usr/bin/env bash
set -e
set -x
set -o pipefail


VIA_CURL=""
IMPORTER="$PWD/importer.py"
BASE_URL="https://raw.githubusercontent.com/appsembler/msft-courses/master"
COURSES_DIR="$PWD"
DATA_DIR="/edx/var/edxapp/data/"

cleanup_data_dir() {
    sudo find "$DATA_DIR" -maxdepth 1 -mindepth 1 -exec rm -rf "{}" \;
}

if [ -d /edx/src ]; then
    EDXAPP_ENV=devstack_appsembler
else
    EDXAPP_ENV=aws_appsembler
fi

if [ "$0" == "bash" ]; then
    if [ -z "$1" ]; then
        VIA_CURL="true"
        IMPORTER=$(mktemp /tmp/abc-script.XXXXXXXX)
        curl "$BASE_URL/importer.py" | tee "$IMPORTER"
        chmod a+wrx "$IMPORTER"
    fi
fi


cleanup_data_dir

CMS_SHELL="sudo -u edxapp /edx/bin/python.edxapp /edx/bin/manage.edxapp lms --settings=$EDXAPP_ENV shell"
echo "__file__='$IMPORTER'; START_DATE='$START_DATE'; END_DATE='$END_DATE'; COURSES_DIR='$COURSES_DIR'; execfile(__file__);" | $CMS_SHELL

cleanup_data_dir
