import os
import os.path
import json
import yaml
from urlparse import urlparse
import zipfile
from zipfile import ZipFile


def is_valid_json(data):
    try:
        json.loads(data)
        return True
    except:
        return False

def parse_yaml(contents):
    return yaml.load(contents)

def read_file(filename):
    with open(filename, 'r') as f:
        contents = f.read()
    return contents

def zip_file(filename):
    arch_name = filename.rsplit('/', 1)[1]
    zip_filename = filename + '.zip'
    with ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.write(filename, arch_name)
    return zip_filename

def get_zip_contents(zip_filename):
    with open(zip_filename, 'rb') as zip_blob:
        return zip_blob.read()

def file_exists(config_path):
    return True if os.path.isfile(config_path) else False

def get_host(url):
    url_obj = urlparse(url)
    return url_obj.hostname

def get_path(url):
    url_obj = urlparse(url)
    return url_obj.path[1:]

def get_scheme(url):
    url_obj = urlparse(url)
    return url_obj.scheme
