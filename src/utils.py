import yaml
from urlparse import urlparse
from zipfile import ZipFile
import os


def parse_yaml(contents):
    return yaml.load(contents)


def read_file(filename):
    with open(filename, 'r') as f:
        contents = f.read()
    return contents


def write_file(filename, content):

    if not os.path.exists(os.path.dirname(filename)):
        try:
            os.makedirs(os.path.dirname(filename))
        except OSError as exc:  # Guard against race condition
            if exc.errno != errno.EEXIST:
                raise

    with open(filename, "w") as f:
        f.write(content)


def zip_file(filename):
    zip_filename = filename + '.zip'
    with ZipFile(zip_filename, 'w') as zf:
        zf.write(filename)
        for root, dirs, files in os.walk('node_modules'):
            for file in files:
                zf.write(os.path.join(root, file))

    return zip_filename


def get_zip_contents(zip_filename):
    with open(zip_filename) as zip_blob:
        return zip_blob


def get_host(url):
    url_obj = urlparse(url)
    return url_obj.hostname


def get_path(url):
    url_obj = urlparse(url)
    return url_obj.path[1:]

def get_scheme(url):
    url_obj = urlparse(url)
    return url_obj.scheme
