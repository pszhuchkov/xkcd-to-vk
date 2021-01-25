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


def download_image(url, filename):
    response = requests.get(url)
    response.raise_for_status()
    with open(filename, 'wb') as file:
        file.write(response.content)


def get_wall_upload_server(group_id, access_token, url=VK_API_URL):
    params = {
        'group_id': group_id,
        'access_token': access_token,
        'v': VK_API_VERSION
    }
    response = requests.get(url.format('photos.getWallUploadServer'),
                            params=params)
    decoded_response = response.json()
    check_errors_in_response(decoded_response)
    upload_url = decoded_response['response']['upload_url']
    return upload_url


def upload_image_to_server(url, file):
    with open(file, 'rb') as file:
        files = {'photo': file}
        response = requests.post(url, files=files)
        decoded_response = response.json()
        check_errors_in_response(decoded_response)
    return {
        'server': decoded_response['server'],
        'photo': decoded_response['photo'],
        'hash': decoded_response['hash']
    }


def save_image_to_group_album(server, photo, hash_code, group_id,
                              access_token, url=VK_API_URL):
    params = {
        'server': server,
        'photo': photo,
        'hash': hash_code,
        'access_token': access_token,
        'v': VK_API_VERSION,
        'group_id': group_id
    }
    response = requests.post(url.format('photos.saveWallPhoto'),
                             params=params)
    decoded_response = response.json()
    check_errors_in_response(decoded_response)
    owner_id = decoded_response['response'][0]['owner_id']
    media_id = decoded_response['response'][0]['id']
    return owner_id, media_id


def make_publication(owner_id, media_id, title, comments,
                     group_id, access_token, url=VK_API_URL):
    params = {
        'owner_id': f'-{group_id}',
        'from_group': 1,
        'attachments': f'photo{owner_id}_{media_id}',
        'message': f'{title}\n\n{comments}',
        'access_token': access_token,
        'v': VK_API_VERSION
    }
    response = requests.get(url.format('wall.post'), params=params)
    decoded_response = response.json()
    check_errors_in_response(decoded_response)


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
    decoded_response = response.json()
    return decoded_response


def check_errors_in_response(decoded_response):
    if 'error' in decoded_response:
        error_message = decoded_response['error']['error_msg']
        raise HTTPError(error_message)


def main():
    load_dotenv()
    group_id = os.getenv('VK_GROUP_ID')
    access_token = os.getenv('VK_ACCESS_TOKEN')
    comic_image_filename = 'random_comic.png'
    try:
        random_comic_id = randint(1, get_last_comic_id())
        comic_properties = get_comic_properties(random_comic_id)
        download_image(comic_properties['img'], comic_image_filename)
        upload_url = get_wall_upload_server(group_id, access_token)
        uploading_properties = upload_image_to_server(upload_url,
                                                      comic_image_filename)
        owner_id, media_id = save_image_to_group_album(
            uploading_properties['server'],
            uploading_properties['photo'],
            uploading_properties['hash'],
            group_id,
            access_token
        )
        make_publication(
            owner_id, media_id,
            comic_properties['title'],
            comic_properties['alt'],
            group_id,
            access_token
        )
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
