#!/usr/bin/env bash
set -e
set -x
set -o pipefail


WORKING_DIRECTORY="$PWD"
DATA_DIR="/edx/var/edxapp/data/"

cleanup_data_dir() {
    sudo find "$DATA_DIR" -maxdepth 1 -mindepth 1 -exec rm -rf "{}" \;
}

delete_course() {
    if [ -d /edx/src ]; then
        EDXAPP_ENV=devstack_appsembler
    else
        EDXAPP_ENV=aws_appsembler
    fi

    cleanup_data_dir

    echo -e 'y\ny' | sudo -u edxapp -- /edx/bin/python.edxapp /edx/bin/manage.edxapp cms \
         --setting="$EDXAPP_ENV" delete_course "$1"

    cleanup_data_dir
}

cat "$WORKING_DIRECTORY/courses-to-delete.txt"

echo "Deleting the courses above..."
echo "The script will wait for 10 seconds, it can be interrupted via Ctrl+C."
echo "After that the deletion process will proceed without confirmation"

seq 0 9 | tac | xargs -L1 -I[] -- bash -c 'sleep 1 && echo -ne "\b[]"'

echo "Deleting..."

while read course_id
do
   if [ -n "$course_id" ]; then
       delete_course "$course_id"
   fi
done < "$WORKING_DIRECTORY/courses-to-delete.txt"

echo "Deleting is Finished"
