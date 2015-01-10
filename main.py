# -*- coding: utf8 -*-

import settings
from pathlib2 import *
import re
import requests
from pyquery import PyQuery
import json


source_dir = 'Z:\TDDOWNLOAD'
target_dir = 'Z:\AV2'

def find_bango_in_file(file):
    """
    :type file: PurePath
    """
    filename = file.name.decode('gbk').encode('utf8')
    # print("processing %s", file.as_uri())
    bango = re.match('([a-zA-Z]{2,6})-?(\d{2,5})', filename)
    if bango:
        dmmbango = bango.expand('\g<1>00\g<2>')
        print("Found bango: %s, expand to dmm format: %s" % (bango.group(), dmmbango))
        return dmmbango
        #return bango.group()
    else:
        print("Not found bango")
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
        #u'商品発売日：': 'saledates',
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
    #item['saledates'] = timelib.strtodatetime(
    #    item['saledates'].text()).strftime("%Y-%m-%d")
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
    """
    :type search_result: requests
    """

    search_result = requests.get("http://www.dmm.co.jp/digital/videoa/-/detail/=/cid=" + bango)
    if search_result.status_code != 200:
        return None

    video = parse_video(search_result.text)
    print("Video detail: %s" % json.dumps(video, ensure_ascii=False))
    return video

def arrange_file(video, file):

    return 0

files = Path(source_dir).glob('**/*.avi')

for file in files:
    bango = find_bango_in_file(file)
    if bango:
        video = get_video_detail(bango)
        arrange_file(video, file)
        exit()
    #exit()