import json
from glob import glob
import subprocess
from os import path, walk, mkdir, makedirs, listdir, environ
from dateutil import parser
import datetime
import fileinput
import yaml
import sys
import shutil
import tarfile
from bs4 import BeautifulSoup
import pytz

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


DATA_DIR = '/edx/var/edxapp/data'  # settings.GITHUB_REPO_ROOT
WORK_TMP_DIR = '/tmp/courses-workdir'
ZIP_EXTRACT_DIR = path.join(WORK_TMP_DIR, 'zip_dest')
XML_EXTRACT_DIR = path.join(WORK_TMP_DIR, 'xml_root')

super_user_id = 5


def _get_start_date():
    # if START_DATE:
    return datetime.datetime(2019, 4, 23, 1, 1, 1, tzinfo=pytz.UTC)
    # return '2019-04-23 01:01:01+00:00'
    # return parser.parse(START_DATE).replace(tzinfo=pytz.UTC)


def _get_end_date():
    # if END_DATE:
    return datetime.datetime(2019, 4, 23, 1, 1, 1, tzinfo=pytz.UTC)
    # return '2019-04-23 01:01:01+00:00'
        # return parser.parse(END_DATE).replace(tzinfo=pytz.UTC)


def _get_courses_dir():
    """
    This is set via `import.sh` at run time.
    """
    return COURSES_DIR


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

    course_id, run = parts[-2:]  # Microsoft course file naming convention

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


def import_single_course(filename):
    print >> sys.stderr, 'IMPORTING course:', filename
    course_id, course_run = _filename_to_id_and_run(filename)

    course_full_id = 'course-v1:Microsoft+{id}+{run}'.format(
        id=course_id,
        run=course_run
    )

    print
    print
    print 'Before import start=', modulestore().get_course(CourseKey.from_string(course_full_id)).start, type(
        modulestore().get_course(CourseKey.from_string(course_full_id)).start)
    print 'Before import enrollment_start=', modulestore().get_course(CourseKey.from_string(course_full_id)).enrollment_start, type(
        modulestore().get_course(CourseKey.from_string(course_full_id)).enrollment_start)
    print 'Before import end=', modulestore().get_course(CourseKey.from_string(course_full_id)).end, type(modulestore().get_course(CourseKey.from_string(course_full_id)).end)
    print 'Before import enrollment_end=', modulestore().get_course(CourseKey.from_string(course_full_id)).enrollment_end, type(
        modulestore().get_course(CourseKey.from_string(course_full_id)).enrollment_end)
    print
    print

    course_xml_dir = path.join(XML_EXTRACT_DIR, '{id}-{run}'.format(id=course_id, run=course_run))
    mkdir(course_xml_dir)

    subprocess.call(['tar', '-xzf', filename, '-C', course_xml_dir])

    _fix_library_source_bug(course_xml_dir)

    print >> sys.stderr, 'IMPORTING course:', course_full_id
    course_items = import_course_from_xml(
        store=modulestore(),
        user_id=super_user_id,
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

        print
        print
        print 'Before save start=', modulestore().get_course(course_id).start, type(
            modulestore().get_course(course_id).start)
        print 'Before save enrollment_start=', modulestore().get_course(course_id).enrollment_start, type(
            modulestore().get_course(course_id).enrollment_start)
        print 'Before save end=', modulestore().get_course(course_id).end, type(modulestore().get_course(course_id).end)
        print 'Before save enrollment_end=', modulestore().get_course(course_id).enrollment_end, type(
            modulestore().get_course(course_id).enrollment_end)
        print
        print

        # with modulestore().bulk_operations(course_id):
        if True:
            descriptor = modulestore().get_course(course_id)

            if _get_start_date():
                print >> sys.stderr, 'Setting start date:', course_id, '=', _get_start_date()
                descriptor.enrollment_start = _get_start_date()
                descriptor.start = _get_start_date()

            if _get_end_date():
                print >> sys.stderr, 'Setting end date:', course_id, '=', _get_end_date()
                descriptor.enrollment_end = _get_end_date()
                descriptor.end = _get_end_date()

            print
            print
            print 'Dirty start=', descriptor.start, type(descriptor.start)
            print 'Dirty enrollment_start=', descriptor.enrollment_start, type(descriptor.enrollment_start)
            print 'Dirty end=', descriptor.end, type(descriptor.end)
            print 'Dirty enrollment_end=', descriptor.enrollment_end, type(descriptor.enrollment_end)
            print
            print

            # if course_updates:
            #     from openedx.core.djangoapps.models.course_details import CourseDetails

            print 'modulestore().update_item', modulestore().update_item
            modulestore().update_item(descriptor, super_user_id)

            print
            print
            print 'After save start=', modulestore().get_course(course_id).start, type(modulestore().get_course(course_id).start)
            print 'After save enrollment_start=', modulestore().get_course(course_id).enrollment_start, type(modulestore().get_course(course_id).enrollment_start)
            print 'After save end=', modulestore().get_course(course_id).end, type(modulestore().get_course(course_id).end)
            print 'After save enrollment_end=', modulestore().get_course(course_id).enrollment_end, type(modulestore().get_course(course_id).enrollment_end)
            print
            print

            # CourseDetails.update_from_json(course_id, course_updates, SystemUser())


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
        store=modulestore(),
        user_id=super_user_id,
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
