import dateutil
import json
from glob import glob
import subprocess
from os import path, walk, mkdir, makedirs, listdir
from pytz import utc
import fileinput
import yaml
import sys
import shutil
import tarfile
from bs4 import BeautifulSoup

from django.conf import settings
from django.contrib.auth.models import User
from xmodule.modulestore import ModuleStoreEnum
from django_comment_common.utils import (
    seed_permissions_roles,
    are_permissions_roles_seeded,
)

from opaque_keys.edx.keys import CourseKey
from opaque_keys.edx.locator import LibraryLocator

from xmodule.contentstore.django import contentstore
from xmodule.modulestore.django import modulestore
from xmodule.modulestore.xml_importer import (
    import_course_from_xml,
    import_library_from_xml
)


MOD_STORE = modulestore()
DATA_DIR = '/edx/var/edxapp/data'  # settings.GITHUB_REPO_ROOT
WORK_TMP_DIR = '/tmp/courses-workdir'
ZIP_EXTRACT_DIR = path.join(WORK_TMP_DIR, 'zip_dest')
XML_EXTRACT_DIR = path.join(WORK_TMP_DIR, 'xml_root')


def _get_courses_dir():
    """
    This is set via `import.sh` at run time.
    """
    return COURSES_DIR


def _get_course_start_date():
    """
    This is set via `import.sh` at run time.
    """
    if COURSE_START_DATE:
        try:
            start = dateutil.parser.parse(COURSE_START_DATE)
        except (AttributeError, ValueError):
            return False

        if start.tzinfo is None:
            start = start.replace(tzinfo=utc)
        return start
    else:
        return False


def _get_course_end_date():
    """
    This is set via `import.sh` at run time.
    """
    if COURSE_END_DATE:
        try:
            end = dateutil.parser.parse(COURSE_END_DATE)
        except (AttributeError, ValueError):
            return False

        if end.tzinfo is None:
            end = end.replace(tzinfo=utc)
        return end
    else:
        return False


def _read_file_in_tgz(filename, sub_filename):
    with tarfile.open(filename, 'r:gz') as tgz:
        file_obj = tgz.extractfile(sub_filename)

        if file_obj:
            return file_obj.read()


def _is_library_file(filename):
    try:
        return bool(_read_file_in_tgz(filename, 'library/library.xml'))
    except KeyError:
        return False


def _filename_to_id_and_run(filename):
    basename = path.basename(filename).replace('.tar.gz', '')
    parts = basename.split('-')

    if len(parts) == 3:
        course_id, run = parts[-2:]  # Microsoft course file naming convention
    elif len(parts) == 4:  # some courses have hyphenated ids.  Assume an additional hyphen is in id
        course_id = '-'.join((parts[1], parts[2]))
        run = parts[3]
    else:
        raise ValueError("Invalid filename, too many or too few hyphens")


    return course_id.strip(), run.strip()


def cleanup():
    if path.exists(WORK_TMP_DIR):
        shutil.rmtree(WORK_TMP_DIR)

    mkdir(WORK_TMP_DIR)
    mkdir(XML_EXTRACT_DIR)
    mkdir(ZIP_EXTRACT_DIR)


def extract_zip_courses():
    for parent, _dirs, files in walk(_get_courses_dir()):
        for zipfile in files:
            if zipfile.endswith('.zip'):
                subprocess.call(['unzip', path.join(parent, zipfile), '-d', ZIP_EXTRACT_DIR])


def get_importable_files(get_courses=False):
    """
    get_courses ^ _is_library_file(path):
        GT_CRS  IS_LIB  XOR
        0	    0	    0
        0	    1	    1
        1	    0	    1
        1	    1	    0


    :param get_courses:
    :return:
    """
    for courses_dir in [ZIP_EXTRACT_DIR, _get_courses_dir()]:
        for parent, _dirs, files in walk(courses_dir):
            for lib_file in files:
                if lib_file.endswith('.tar.gz'):
                    if get_courses ^ _is_library_file(path.join(parent, lib_file)):
                        yield path.join(parent, lib_file)


def _fix_library_source_bug(course_xml_dir):
    libraries_dir = path.join(course_xml_dir, 'course/library_content/')

    if not path.exists(libraries_dir):
        return

    for library_file in listdir(libraries_dir):
        library_file = path.join(libraries_dir, library_file)

        with open(library_file, 'r') as library_f:
            lib_xml = BeautifulSoup(library_f.read(), 'lxml')
            lib_element = lib_xml.library_content

        with open(library_file, 'w') as library_f:
            del lib_element['source_library_version']
            library_f.write(str(lib_element))


def _set_course_dates(course_id):
    start = _get_course_start_date()
    end = _get_course_end_date()
    course = MOD_STORE.get_course(course_id)

    if start:
        print >> sys.stderr, 'Setting course start date for ', course_id, 'to', start
        course.start = start

    if end:
        print >> sys.stderr, 'Setting course end date for ', course_id, 'to', end
        course.end = end

    if start or end:
        course.save()
        MOD_STORE.update_item(course, course._edited_by)


def import_single_course(filename):
    print >> sys.stderr, 'IMPORTING course:', filename
    course_id, course_run = _filename_to_id_and_run(filename)

    course_full_id = 'course-v1:Microsoft+{id}+{run}'.format(
        id=course_id,
        run=course_run
    )

    course_xml_dir = path.join(XML_EXTRACT_DIR, '{id}-{run}'.format(id=course_id, run=course_run))
    mkdir(course_xml_dir)

    subprocess.call(['tar', '-xzf', filename, '-C', course_xml_dir])

    _fix_library_source_bug(course_xml_dir)

    print >> sys.stderr, 'IMPORTING course:', course_full_id
    course_items = import_course_from_xml(
        store=MOD_STORE,
        user_id=ModuleStoreEnum.UserID.mgmt_command,
        data_dir=DATA_DIR,
        source_dirs=[path.join(course_xml_dir, 'course')], # Open edX needs `course` dir
        load_error_modules=False,
        static_content_store=contentstore(),
        verbose=True,
        do_import_static=True,
        target_id=CourseKey.from_string(course_full_id),
        create_if_not_present=True,
    )

    for course in course_items:
        course_id = course.id
        if not are_permissions_roles_seeded(course_id):
            print >> sys.stderr, 'Seeding forum roles for course', course_id
            seed_permissions_roles(course_id)
        _set_course_dates(course_id)


def import_single_library(filename):
    print >> sys.stderr, 'IMPORTING library:', filename
    no_extension = path.basename(filename).replace('.tar.gz', '')

    library_xml_dir = path.join(XML_EXTRACT_DIR, no_extension)
    mkdir(library_xml_dir)
    subprocess.call(['tar', '-xzf', filename, '-C', library_xml_dir])

    with open(path.join(library_xml_dir, 'library/library.xml')) as lib_xml_file:
        lib_xml = BeautifulSoup(lib_xml_file.read())
        lib_element = lib_xml.find('library')
        target_id = LibraryLocator(org=str(lib_element['org']), library=str(lib_element['library']))

    print >> sys.stderr, 'IMPORTING library:', target_id
    import_library_from_xml(
        store=MOD_STORE,
        user_id=ModuleStoreEnum.UserID.mgmt_command,
        data_dir=DATA_DIR,
        source_dirs=[path.join(library_xml_dir, 'library')],  # Open edX needs `library` dir
        load_error_modules=False,
        static_content_store=contentstore(),
        verbose=True,
        do_import_static=True,
        target_id=target_id,
        create_if_not_present=True,
    )


def run():
    cleanup()
    extract_zip_courses()
    for library_file in get_importable_files(get_courses=False):
        import_single_library(library_file)

    for course_filename in get_importable_files(get_courses=True):
        import_single_course(course_filename)


run()
