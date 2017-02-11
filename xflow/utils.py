import os
import os.path
import json
import yaml
import inspect
from urlparse import urlparse
import zipfile
from zipfile import ZipFile


def is_valid_json(contents):
    try:
        json.loads(contents)
        return True
    except:
        return False


def parse_yaml(contents):
    return yaml.load(contents)


def read_file(filename):
    with open(filename, 'r') as f:
        contents = f.read()
    return contents


def write_file(filename, contents):
    with open(filename, 'w') as f:
        f.write(contents)


def zip_file(filename, otherfiles=None):
    def get_arcname(fname):
        splitted = fname.rsplit('/', 1)
        return splitted[1] if len(splitted) > 1 else splitted[0]

    zip_filename = filename + '.zip'
    with ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.write(filename, get_arcname(filename))
        otherfiles = otherfiles or []
        for of in otherfiles:
            zf.write(of, get_arcname(of))
    return zip_filename


def is_local_file(path):
    return True if not get_scheme(path) and \
                   not path.endswith('zip') else False


def is_local_zip_file(path):
    return True if not get_scheme(path) and \
                   path.endswith('zip') else False


def is_s3_file(path):
    return True if get_scheme(path) == 's3' else False


def get_zip_contents(zip_filename):
    with open(zip_filename, 'rb') as zip_blob:
        return zip_blob.read()


def file_exists(config_path):
    return True if os.path.isfile(config_path) else False


def get_project_directory():
    filepath = os.path.abspath(inspect.stack()[0][1])
    return filepath.rsplit('/', 2)[0]

def get_host(url):
    url_obj = urlparse(url)
    return url_obj.hostname


def get_path(url):
    url_obj = urlparse(url)
    return url_obj.path[1:]


def get_resource(url):
    url_obj = urlparse(url)
    return url_obj.path.rsplit('/', 1)[-1]


def get_scheme(url):
    url_obj = urlparse(url)
    return url_obj.scheme


def get_name_from_arn(arn):
    return arn.rsplit(":", 1)[1]


def format_datetime(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
