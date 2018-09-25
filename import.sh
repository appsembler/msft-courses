#!/usr/bin/env bash
set -e
set -x
set -o pipefail


COURSES_DIR="$PWD"
DATA_DIR="/edx/var/edxapp/data/"
COURSE_START_DATE=${COURSE_START_DATE:=""}
COURSE_END_DATE=${COURSE_END_DATE:=""}

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
        BASE_URL="https://raw.githubusercontent.com/appsembler/msft-courses/master"
        IMPORTER=$(mktemp /tmp/abc-script.XXXXXXXX)
        curl "$BASE_URL/importer.py" | tee "$IMPORTER"
        chmod a+wrx "$IMPORTER"
    fi
else
    SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null && pwd )"
    IMPORTER="$SCRIPT_DIR/importer.py"
fi


cleanup_data_dir

CMS_SHELL="sudo -u edxapp /edx/bin/python.edxapp /edx/bin/manage.edxapp cms --settings=$EDXAPP_ENV shell"
echo "__file__='$IMPORTER'; COURSES_DIR='$COURSES_DIR'; COURSE_START_DATE='$COURSE_START_DATE'; COURSE_END_DATE='$COURSE_END_DATE'; execfile(__file__);" | $CMS_SHELL

cleanup_data_dir
