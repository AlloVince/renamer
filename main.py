# -*- coding: utf8 -*-

import settings
from pathlib2 import *
import re
import requests
from pyquery import PyQuery
import json
import os
import logging
import traceback

source_dir = 'Z:\Issue'
target_dir = 'Z:\dist'
rename_format = '%actor% - %title% [%bango%]'
# Debug:
# logging.basicConfig(level=logging.INFO)

def print_path(file):
    return file.as_posix().decode('gbk').encode('utf8')

def find_bango_in_file(file):
    logging.warning("--------------------------------------------------------------------------------------")
    logging.warning("Processing: %s" % print_path(file))
    """
    :type file: PurePath
    """
    filename = file.name.decode('gbk').encode('utf8')
    # print("processing %s", file.as_uri())
    bango = re.search(r'([a-zA-Z]{2,6})-?(\d{2,5})', filename)
    if bango:
        logging.warning("Found bango: %s" % bango.group())
        return bango.group()
    else:
        logging.warning("Result: Not found bango, skiped")
        return None


def get_movie_detail(bango):
    # Try search for once
    search_url = "http://yinxing.com/v1/movies?q="
    search_result = requests.get(
        search_url + bango, timeout=2)
    logging.warning(
        "Try search bango: %s" % search_url + bango)

    if search_result.status_code != 200:
        logging.warning("Result: not found in website by %s in %s" % (search_result.status_code, search_result.url))
        return None
    search_result = json.loads(search_result.text)
    # print search_result['items'][0]['link']
    # print re.search("-/detail/=", search_result['items'][0]['link'])
    if len(search_result['results']) < 1:
        logging.warning("Result: not found %s in %s" % (search_result.status_code, search_result.url))
        return None
    return search_result['results'][0]

def path_filter(name):
    name = name.replace('/', '.')
    # name = name.replace('・', '.')
    return name


def arrange_file(movie, file):
    maker = movie['maker']['name'] if movie['maker'] else 'unknown'
    logging.warning("movie %s" % movie)
    target_path = target_dir + '/' + path_filter(maker).encode("gbk")
    logging.warning("Target path: %s" % print_path(Path(target_path)))
    if Path(target_path).exists() is False:
        Path(target_path).mkdir(parents=True, mode=0o777)
        logging.warning("Target path not exists and be created")

    casts = movie["casts"]
    casts_list = []
    for cast in casts:
        casts_list.append(cast["name"])
    casts_list.reverse()
    casts = "" if len(casts_list) < 1 else ", ".join(casts_list) + " - "
    target_file = "%s%s [%s]" % (casts, path_filter(movie['title']), path_filter(movie['banngo']))
    target_cover = target_path + "/" + (target_file + '.jpg').encode("gbk")
    target_file = target_path + "/" + (target_file + file.suffix).encode("gbk")

    if Path(target_cover).exists():
        logging.error("Result: Target %s exists, skiped" % print_path(Path(target_file)))
        return None

    if Path(target_cover).exists() is False:
        response = requests.get(movie["images"][2], timeout=2)
        if response.ok:
            open(target_cover, "wb").write(response.content)
            logging.info("Download cover from %s" % (response.url))
        else:
            logging.warning("Result: Download cover failed, not move")
            return None

    # Real Move
    file.rename(Path(target_file))
    # Fake move
    # Path(target_file).touch(exist_ok=True)
    logging.warning("Result: Move to target file: %s" % print_path(Path(target_file)))
    return target_file


def humansize(nbytes):
    suffixes = ['B', 'KB', 'MB', 'GB', 'TB', 'PB']
    if nbytes == 0: return '0 B'
    i = 0
    while nbytes >= 1024 and i < len(suffixes) - 1:
        nbytes /= 1024.
        i += 1
    f = ('%.2f' % nbytes).rstrip('0').rstrip('.')
    return '%s %s' % (f, suffixes[i])


def rmdirtree(target_dir):
    for dir, dirs, files in os.walk(target_dir, topdown=False):
        for name in files:
            os.remove(os.path.join(dir, name))
        for name in dirs:
            os.rmdir(os.path.join(dir, name))
    os.rmdir(target_dir)


def delete_empty_dir(file):
    logging.debug("Parent dir: %s" % file.parent)
    if file.parent == Path(source_dir):
        return None

    size = 0
    for subfile in file.parent.glob('**/*'):
        size += subfile.stat().st_size

    # small than 20MB, remove
    if size < 20000000:
        rmdirtree(file.parent.as_posix())
        logging.info("Dir %s size %s, removed" % (file, humansize(size)))
    else:
        logging.info("Dir %s size %s, not remove" % (file, humansize(size)))


def process(file):
    bango = find_bango_in_file(file)
    if not bango:
        return None
    movie = get_movie_detail(bango)
    if not movie:
        return None
    res = arrange_file(movie, file)
    delete_empty_dir(file)


# single file test:
# process(Path("Z:/somefile"))
# print(bango_to_dmmbango("dv1687"))


for ext in ["avi", "mkv", "mp4"]:
    files = Path(source_dir).rglob('*.' + ext)
    for cfile in files:
        try:
            process(cfile)
        except:
            # logging.warning("Result: Unkown exception happens for %s, detail:\n %s" % (print_path(cfile), traceback.print_exc()))
            continue
