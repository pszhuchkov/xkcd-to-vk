import os
import sys
import time

import requests

from dotenv import load_dotenv
from pathlib import Path
from random import randint
from requests.exceptions import ConnectionError, HTTPError


COMIC_API_URL = 'http://xkcd.com/{}/info.0.json'
VK_API_URL = 'https://api.vk.com/method/{}'
VK_API_VERSION = '5.126'
VK_GROUP_ID = 202069060


def download_image(url, filename):
    response = requests.get(url)
    response.raise_for_status()
    with open(filename, 'wb') as file:
        file.write(response.content)


def get_wall_upload_server(group_id=VK_GROUP_ID, url=VK_API_URL):
    params = {
        'group_id': group_id,
        'access_token': os.getenv('VK_ACCESS_TOKEN'),
        'v': VK_API_VERSION
    }
    response = requests.get(url.format('photos.getWallUploadServer'),
                            params=params)
    response.raise_for_status()
    response_decoded = response.json()
    upload_url = response_decoded['response']['upload_url']
    return upload_url


def upload_and_save_image(url, file):
    with open(file, 'rb') as file:
        files = {'photo': file}
        response = requests.post(url, files=files)
        response.raise_for_status()
        response_decoded = response.json()
    owner_id, media_id = save_image(response_decoded['server'],
                                    response_decoded['photo'],
                                    response_decoded['hash'])
    return owner_id, media_id


def save_image(server, photo, hash_code,
               group_id=VK_GROUP_ID, url=VK_API_URL):
    params = {
        'server': server,
        'photo': photo,
        'hash': hash_code,
        'access_token': os.getenv('VK_ACCESS_TOKEN'),
        'v': VK_API_VERSION,
        'group_id': group_id
    }
    response = requests.post(url.format('photos.saveWallPhoto'),
                             params=params)
    response.raise_for_status()
    response_decoded = response.json()['response'][0]
    return response_decoded['owner_id'], response_decoded['id']


def make_publication(owner_id, media_id, title, comments,
                     group_id=VK_GROUP_ID, url=VK_API_URL):
    params = {
        'owner_id': -group_id,
        'from_group': 1,
        'attachments': f'photo{owner_id}_{media_id}',
        'message': f'{title}\n\n{comments}',
        'access_token': os.getenv('VK_ACCESS_TOKEN'),
        'v': VK_API_VERSION
    }
    response = requests.get(url.format('wall.post'), params=params)
    response.raise_for_status()


def get_last_comic_id(url=COMIC_API_URL):
    url = url.format('')
    response = requests.get(url)
    response.raise_for_status()
    last_comic_id = response.json()['num']
    return last_comic_id


def get_comic_properties(comic_id, url=COMIC_API_URL):
    url = url.format(comic_id)
    response = requests.get(url)
    response.raise_for_status()
    response_decoded = response.json()
    return response_decoded


def main():
    load_dotenv()
    comic_image_filename = 'random_comic.png'
    try:
        random_comic_id = randint(1, get_last_comic_id())
        comic_properties = get_comic_properties(random_comic_id)
        download_image(comic_properties['img'], comic_image_filename)
        upload_url = get_wall_upload_server()
        owner_id, media_id = upload_and_save_image(
            upload_url,
            comic_image_filename
        )
        make_publication(
            owner_id, media_id,
            comic_properties['title'],
            comic_properties['alt']
        )
        print(f'''Comic "{comic_properties['title']}" is published''')
    except ConnectionError as conn_err:
        print(conn_err, file=sys.stderr)
        time.sleep(3)
        main()
    except HTTPError as http_err:
        print(http_err, file=sys.stderr)
        sys.exit()
    finally:
        Path(comic_image_filename).unlink(missing_ok=True)


if __name__ == '__main__':
    main()
