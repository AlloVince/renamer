# -*- coding: utf8 -*-

import settings
from pathlib2 import *
import re
import requests
from pyquery import PyQuery
import json
import os
import logging

source_dir = 'Z:\TDDOWNLOAD'
target_dir = 'Z:\AV2'
rename_format = '%actor% - %title% [%bango%]'
logging.basicConfig(level=logging.INFO)


def find_bango_in_file(file):
    logging.info("---------------------------\nProcessing: %s" % file.as_posix().decode('gbk').encode('utf8'))
    """
    :type file: PurePath
    """
    filename = file.name.decode('gbk').encode('utf8')
    # print("processing %s", file.as_uri())
    bango = re.search(r'([a-zA-Z]{2,6})-?(\d{2,5})', filename)
    if bango:
        dmmbango = bango.expand('\g<1>00\g<2>')
        logging.info("Found bango: %s, expand to dmm format: %s" % (bango.group(), dmmbango))
        return dmmbango
        # return bango.group()
    else:
        logging.info("Not found bango")
        return None


def parse_video(html):
    item = {}
    dom = PyQuery(html)
    item['title'] = dom("#title").text()
    item['image_urls'] = [dom("#sample-video > a").eq(0).attr('href')]
    item['symbol_original'] = dom("#sample-video > a").eq(0).attr('id')
    if not item['symbol_original']:
        item['symbol_original'] = dom("input[name=content_id]").eq(0).attr('value')

    if not item['symbol_original']:
        return []
    p = re.compile(r'(\d*)([a-zA-Z]+)00(\d+)')
    item['symbol'] = p.sub(r'\2\3', item['symbol_original'])

    def links_to_list(links):
        res = []
        for link in links.find('a').items():
            res.append({
                'id': re.findall('id=(\d+)', link.attr('href'))[0],
                'name': link.text(),
            })
        return res

    meta_map = {
        u'出演者：': 'casts',
        u'監督：': 'directors',
        u'配信開始日：': 'pubdates',
        # u'商品発売日：': 'saledates',
        u'メーカー：': 'maker',
        u'レーベル：': 'maker_label',
        u'収録時間：': 'durations',
        u'出演者：': 'casts',
        u'シリーズ：': 'series',
        u'ジャンル：': 'tags',
        u'平均評価：': 'rating',
    }
    meta_table = dom('.page-detail table.mg-b20').eq(0)
    for meta in meta_table.find('tr'):
        meta = PyQuery(meta).find('td')
        meta_title = meta.eq(0).text().rstrip().lstrip()
        if meta_title and meta_map.get(meta_title):
            meta_key = meta_map[meta_title]
            item[meta_key] = meta.eq(1)

    item['casts'] = links_to_list(item['casts'])
    item['directors'] = links_to_list(item['directors'])
    item['maker'] = links_to_list(item['maker'])
    item['maker_label'] = links_to_list(item['maker_label'])
    item['tags'] = links_to_list(item['tags'])
    item['durations'] = re.findall(u'(\d+)分', item['durations'].text())[0]
    # item['saledates'] = timelib.strtodatetime(
    # item['saledates'].text()).strftime("%Y-%m-%d")
    series = links_to_list(item['series'])
    item['series'] = series[0] if series else None
    item['rating'] = re.findall(
        '(\d+)\.gif', item['rating'].find('img').attr('src'))[0]

    item['summary'] = meta_table.nextAll().eq(1).text()

    photos = []
    for img in dom('#sample-image-block img').items():
        photos.append(img.attr('src').replace('-', 'jp-'))

    item['photos'] = photos
    return item


def get_video_detail(bango):
    url = "http://www.dmm.co.jp/digital/videoa/-/detail/=/cid=" + bango
    logging.info("Try to request url: %s" % url)
    search_result = requests.get(url)
    """
    :type search_result: requests
    """

    if search_result.status_code == 404:
        # Try search for once
        search_result = requests.get("http://www.dmm.co.jp/search/=/n1=FgRCTw9VBA4GAVhfWkIHWw__/searchstr=" + bango)
        logging.info("Try search bango: %s" % "http://www.dmm.co.jp/search/=/n1=FgRCTw9VBA4GAVhfWkIHWw__/searchstr=" + bango)
        # Still not found
        if search_result.status_code != 200:
            return None
        dom = PyQuery(search_result.text)
        items = dom("#list li")
        if items.length > 1:
            logging.error("Found more than 1 result: %s" % "http://www.dmm.co.jp/search/=/n1=FgRCTw9VBA4GAVhfWkIHWw__/searchstr=" + bango)
            return None
        url = items.eq(0).find("a").eq(0).attr("href")
        if not url:
            return None
        logging.info("Re-Try to request url: %s" % url)
        search_result = requests.get(url)

    if search_result.status_code != 200:
        logging.info("Video request failed by: %s" % search_result.status_code)
        return None

    video = parse_video(search_result.text)
    logging.info("Video detail: %s" % json.dumps(video, ensure_ascii=False))
    return video


def arrange_file(video, file):
    target_path = target_dir + '/' + video['maker_label'][0]['name'].encode("gbk")

    logging.info("Target path: %s" % target_path)
    if Path(target_path).exists() is False:
        Path(target_path).mkdir(parents=True, mode=0o777)
        logging.warning("Target path not exists and be created")

    casts = video["casts"]
    casts_list = []
    for cast in casts:
        casts_list.append(cast["name"])
    casts_list.reverse()
    casts = "" if len(casts_list) < 1 else ", ".join(casts_list) + " - "
    target_file = "%s%s [%s]" % (casts, video['title'], video['symbol'])
    target_cover = target_path + "/" + (target_file + '.jpg').encode("gbk")
    target_file = target_path + "/" + (target_file + file.suffix).encode("gbk")

    if Path(target_file).exists():
        logging.error("Target %s exists" % target_file)
        return None

    if Path(target_cover).exists() is False:
        response = requests.get(video["image_urls"][0])
        if response.ok:
            open(target_cover, "wb").write(response.content)
            logging.info("Download cover from %s" % (response.url))
        else:
            logging.warning("Download cover failed, not move")
            return None

    # Real Move
    file.rename(Path(target_file))
    # Fake move
    # Path(target_file).touch(exist_ok=True)
    logging.warning("Move to target file: %s" % target_file.as_posix().decode('gbk').encode('utf8'))
    return target_file


def humansize(nbytes):
    suffixes = ['B', 'KB', 'MB', 'GB', 'TB', 'PB']
    if nbytes == 0: return '0 B'
    i = 0
    while nbytes >= 1024 and i < len(suffixes)-1:
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


for ext in ["avi", "mkv", "mp4"]:
    files = Path(source_dir).rglob('*.' + ext)
    for file in files:
        try:
            bango = find_bango_in_file(file)
            if not bango:
                continue
            video = get_video_detail(bango)
            if not video:
                continue
            res = arrange_file(video, file)
            if not res:
                continue
            delete_empty_dir(file)
        except:
            logging.warning("Exception happens")