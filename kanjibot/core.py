'''
Kanjibot -- a reddit bot that posts information about kanji
Copyright (C) 2017  Vojtech Balak

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''

import base64
import json
import configparser
import os.path
import xml.etree.ElementTree as ET
import requests
import praw
from io import BytesIO
from collections import OrderedDict
from PIL import Image
from PIL import ImageDraw
from PIL import ImageFont


config = None
kanji_data = None
radicals = ''
components = {}


def load_kanji_data():
    ''' Loads dictionary data into memory. '''

    print('Reading radicals... ', end='')
    with open('jp-data/radicals', 'r') as f:
        global radicals
        radicals = f.read().strip()
    print('done')
    print('Reading kanjidic2.xml... ', end='')
    tree = ET.parse('jp-data/kanjidic2.xml')
    global kanji_data
    kanji_data = tree.getroot()
    print('done')
    print('Reading kradfile... ', end='')
    with open('jp-data/kradfile', 'r') as f:
        for line in f:
            parts = line.strip().split(' ')
            components[parts[0]] = parts[2:]
    print('done')
    print('Reading kradfile2... ', end='')
    with open('jp-data/kradfile2', 'r') as f:
        for line in f:
            parts = line.strip().split(' ')
            components[parts[0]] = parts[2:]
    print('done')


def is_kanji(character):
    ''' https://stackoverflow.com/a/30070664 '''

    ranges = [
        {'from': ord(u'\u4e00'), 'to': ord(u'\u9fff')},
        {'from': ord(u'\u3400'), 'to': ord(u'\u4dbf')},
        {'from': ord(u'\U00020000'), 'to': ord(u'\U0002a6df')},
        {'from': ord(u'\U0002a700'), 'to': ord(u'\U0002b73f')},
        {'from': ord(u'\U0002b740'), 'to': ord(u'\U0002b81f')},
        {'from': ord(u'\U0002b820'), 'to': ord(u'\U0002ceaf')}
    ]

    return any(
        [range['from'] <= ord(character) <= range['to'] for range in ranges]
    )


def extract_kanji(string):
    ''' Returns a list of all kanji in a string. '''

    return list(filter(lambda c: is_kanji(c), string))


def upload_to_imgur(image, title=None):
    ''' Uploads an image to imgur and returns its URL. '''
    client_id = config['kanji-bot']['imgur_id']
    url = 'https://api.imgur.com/3/image'
    response = requests.post(
        url,
        headers={'Authorization': 'Client-ID '+client_id},
        data={
            'image': image,
            'type': 'base64',
            'title': title
        }
    )
    response_data = json.loads(response.text)
    if response_data['success']:
        return response_data['data']['link']
    else:
        print('Imgur upload failed!')
        return None


def get_preview_image_url(kanji):
    ''' Uploads kanji image to imgur and returns its url. '''

    image = Image.new("RGBA", (1000, 250), (255, 255, 255))
    draw = ImageDraw.Draw(image)

    ipag = ImageFont.truetype("jp-data/fonts/IPAexfont/ipaexg.ttf", 200)
    ipam = ImageFont.truetype("jp-data/fonts/IPAexfont/ipaexm.ttf", 200)
    nagayama = ImageFont.truetype("jp-data/fonts/nagayama_kai08.otf", 200)
    sanafon = ImageFont.truetype("jp-data/fonts/SNsanafon/SNsanafon.ttf", 200)

    draw.text((25, 25), kanji, (0, 0, 0), font=ipag)
    draw.text((275, 25), kanji, (0, 0, 0), font=ipam)
    draw.text((525, 25), kanji, (0, 0, 0), font=nagayama)
    draw.text((775, 25), kanji, (0, 0, 0), font=sanafon)

    buff = BytesIO()
    image.save(buff, format="PNG")
    img_base64 = base64.b64encode(buff.getvalue())

    return upload_to_imgur(img_base64, kanji+' preview')


def get_stroke_image_url(kanji):
    ''' Uploads kanji stroke order image to imgur and returns its url. '''

    path = 'jp-data/strokes/'+kanji+'.png'
    if os.path.isfile(path):
        with open(path, 'rb') as f:
            img = f.read()
            img_base64 = base64.b64encode(img)
            return upload_to_imgur(img_base64, kanji+' stroke order')
    else:
        return None


def get_kanji_info(kanji, compact=False):
    '''
    Returns a markdown block with information about the specified kanji.
    Will also upload a stroke order image to imgur.
    '''

    data = None
    for character in kanji_data.findall('character'):
        if character.find('literal').text == kanji:
            data = character
            break
    if data is None:
        return '##Couldn\'t find data for kanji \''+kanji+'\''

    if compact:
        small_separator = ' '
        big_separator = '  \n'
    else:
        small_separator = '  \n'
        big_separator = '\n\n'

    comment = ''
    if not compact:
        comment += '##'
    comment += '['+kanji+']('+get_preview_image_url(kanji)+')'
    if compact:
        comment += ' '
    else:
        comment += '\n\n'

    rm = data.find('reading_meaning')
    comment += '**Meaning:** '
    meanings = []
    for meaning in rm.iter('meaning'):
        if 'm_lang' not in meaning.attrib:
            meanings.append(meaning.text)
    comment += ', '.join(meanings)+big_separator

    comment += '**Onyomi:** '
    on = []
    for reading in rm.iter('reading'):
        if reading.attrib['r_type'] == 'ja_on':
            on.append(reading.text)
    if len(on) > 0:
        comment += '、'.join(on)+small_separator
    else:
        comment += '-'+small_separator

    comment += '**Kunyomi:** '
    kun = []
    for reading in rm.iter('reading'):
        if reading.attrib['r_type'] == 'ja_kun':
            kun.append(reading.text)
    if len(kun) > 0:
        comment += '、'.join(kun)+small_separator
    else:
        comment += '-'+small_separator
    comment += '**Nanori:** '
    nanori = []
    for reading in rm.iter('nanori'):
        nanori.append(reading.text)
    if len(nanori) > 0:
        comment += '、'.join(nanori)+big_separator
    else:
        comment += '-'+big_separator

    if not compact:
        misc = data.find('misc')
        misc_info = []
        if misc.find('grade') is not None:
            misc_info.append('**Grade:** '+misc.find('grade').text)
        if misc.find('stroke_count') is not None:
            misc_info.append(
                '**Stroke Count:** '+misc.find('stroke_count').text
            )
        if misc.find('freq') is not None:
            misc_info.append('**Frequency:** '+misc.find('freq').text)
        if misc.find('jlpt') is not None:
            misc_info.append('**JLPT:** '+misc.find('jlpt').text)

        if len(misc_info) > 0:
            comment += ', '.join(misc_info)
            if compact:
                comment += '  \n'
            else:
                comment += '\n\n'

    parts_info = []
    if data.find('radical') is not None:
        for rv in data.find('radical').findall('rad_value'):
            if rv.attrib['rad_type'] == 'classical':
                parts_info.append('**Radical:** '+radicals[int(rv.text)-1])
    if kanji in components:
        parts_info.append('**Components:** '+' '.join(components[kanji]))
    comment += ' '.join(parts_info)

    img = get_stroke_image_url(kanji)
    if img is not None:
        if compact:
            comment += ' '
        else:
            comment += '\n\n'
        comment += '[Stroke Order]('+img+')'

    return comment


def reply_to_mentions():
    ''' Continuously reads reddit mentions and replies to them. '''

    load_kanji_data()

    global config
    config = configparser.ConfigParser()
    config.read('kanjibot.ini')
    account = config['kanji-bot']['reddit_account']
    footer = config['kanji-bot']['footer']
    reddit = praw.Reddit('kanji-bot')

    print('Connected to reddit, waiting for summons...')
    for mention in reddit.inbox.stream():
        print('Reading mention by /u/'+mention.author.name, end='')
        if hasattr(mention.subreddit, 'display_name'):
            print('in /r/'+mention.subreddit.display_name)
        else:
            print()
        for line in mention.body.split('\n'):
            if 'u/'+account in line:
                kanji = OrderedDict.fromkeys(list(extract_kanji(line)[:8]))
                if len(kanji) > 0:
                    print('Found kanji:', ' '.join(kanji))
                    print('Sending response...', end='')
                    reply = [get_kanji_info(k, len(kanji) > 1) for k in kanji]
                    comment = '\n\n---\n\n'.join(reply)
                    comment += '\n\n---\n\n'+footer
                    mention.reply(comment)
                    print(' done')
                    break
                else:
                    print(' no kanji found')
        mention.mark_read()
