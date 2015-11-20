# -*- coding: utf8 -*-
import traceback

import settings
from pathlib2 import *
import re
import requests
import json
import os
import logging

# source_dir = 'Z:\Issue'
source_dir = '/Volumes/TB/TDDOWNLOAD'
# target_dir = 'Z:\dist'
target_dir = '/Volumes/TB/dist'
path_encoding = 'utf8'
rename_format = '%actor% - %title% [%bango%]'


# Debug:
logging.basicConfig(level=logging.INFO)
#logging.basicConfig(level=logging.ERROR)


def print_path(file):
    return file.as_posix().decode(path_encoding).encode('utf8')


def find_banngo_in_file(file):
    logging.info("--------------------------------------------------------------------------------------")
    logging.info("Processing: %s" % print_path(file))
    """
    :type file: PurePath
    """
    filename = file.name.decode(path_encoding).encode('utf8')
    # print("processing %s", file.as_uri())
    banngo = re.search(r'([a-zA-Z]{2,6})-?(\d{2,5})', filename)
    if banngo:
        logging.warning("Found bango: %s" % banngo.group())
        return banngo.group()
    else:
        logging.warning("Result: Not found bango, skiped")
        return None


def get_movie_detail(banngo):
    # Try search for once
    search_url = "http://yinxing.com/v1/movies?q="
    search_result = requests.get(
        search_url + banngo, timeout=2)
    logging.info(
        "Try search banngo: %s" % search_url + banngo)

    if search_result.status_code != 200:
        logging.warning("Result: not found in website by %s in %s" % (search_result.status_code, search_result.url))
        return None
    result = json.loads(search_result.text)

    if len(result['results']) < 1:
        logging.warning("Result: not found %s in %s" % (search_result.status_code, search_result.url))
        return None
    return result['results'][0]


def path_filter(name):
    name = name.replace('/', '.').strip()
    name = name.replace(u'・', '.')
    return name


def arrange_file(movie, file):
    maker = movie['maker']['name'] if movie['maker'] else 'unknown'
    logging.info("Found movie as %s" % movie)
    target_path = target_dir + '/' + path_filter(maker).encode(path_encoding)
    logging.info("Target path: %s" % print_path(Path(target_path)))
    if Path(target_path).exists() is False:
        Path(target_path).mkdir(parents=True, mode=0o777)
        logging.warning("Target path %s not exists and be created" % target_path)

    casts = movie["casts"]
    casts_list = []
    for cast in casts:
        casts_list.append(cast["name"])
    casts_list.reverse()
    casts = "" if len(casts_list) < 1 else ", ".join(casts_list) + " - "
    target_file = "%s%s [%s]" % (casts, path_filter(movie['title']), path_filter(movie['banngo']))
    target_cover = target_path + "/" + (target_file + '.jpg').encode(path_encoding)
    target_file = target_path + "/" + (target_file + file.suffix).encode(path_encoding)

    if Path(target_cover).exists():
        logging.error("TODO: FILE %s target %s exists, skiped" % (file, print_path(Path(target_file))))
        os.remove(file.as_posix())
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
    bango = find_banngo_in_file(file)
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
            logging.warning(
                "Result: Unknown exception happens for %s, detail:\n %s" % (print_path(cfile), traceback.print_exc()))
            continue
