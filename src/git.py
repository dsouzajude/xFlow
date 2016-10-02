import requests
import utils
from urlparse import urlparse
''' This is a simple utility to parse and download
stuff from the github url. To start with, it does a
basic unauthenticated request to download the raw github
user content information.
'''

api_git = 'https://api.github.com'
directory = ''


def parse_git_url(link):
    # Make this function rock solid.
    result = {}

    parsed_info = urlparse(link)
    path = parsed_info.path

    # extract the initial information leading to the blob.
    idx = path.index('blob')
    initial = path[:idx]

    user_repo = initial.strip('/').split('/')

    if len(user_repo) != 2:
        raise Exception('invalid link: ' + link)

    result['username'] = user_repo[0]
    result['repo'] = user_repo[1]

    # blob/ref(branch)/filepath
    file_path = path[idx + 5:]
    ref_path = file_path.split('/', 1)

    if len(ref_path) != 2:
        raise Exception('invalid link: ' + link)

    result['ref'] = ref_path[0]
    result['path'] = ref_path[1]

    return result


def download_git_content(url):
    ''' Based on the information provided for the
    file content location, we extract the important parts from it
    and then we download the raw user content.
    '''
    info = parse_git_url(url)

    payload = {'ref': info['ref']}
    r = requests.get(api_git + '/repos/' + info['username'] +
                     '/' + info['repo'] + '/contents' + info['path'],
                     params=payload)

    if r.status_code != 200:
        raise Exception(
            'Unable to fetch metadata for the information to be downloaded')

    download_url = r.json()['download_url']
    r = requests.get(download_url)

    if r.status_code != 200:
        raise Exception('Unable to fetch the raw content')

    path = info['path']
    file_info = path.rsplit('/', 1)

    utils.write_file('./lambda/' + file_info[1], r.text)


if __name__ == "__main__":
    download_git_content(
        'https://github.com/babbarshaer/mymdb/blob/master/public/css/app.css')
