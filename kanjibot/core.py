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
import requests
import praw
from io import BytesIO
from collections import OrderedDict
from PIL import Image
from PIL import ImageDraw
from PIL import ImageFont

from kanjibot import database


config = configparser.ConfigParser()
config.read('kanjibot.ini')
db = database.Database(
    config['kanji-bot']['db_host'],
    config['kanji-bot']['db_name'],
    config['kanji-bot']['db_user'],
    config['kanji-bot']['db_password'],
)


def init_database():
    ''' Fills the database with data. Should be run only once. '''

    db.fill_database()


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

    data = db.get_kanji_data(kanji)
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

    comment += '**Meaning:** '
    comment + ', '.join(data['meaning'])+big_separator

    comment += '**Onyomi:** '
    if len(data['on']) > 0:
        comment += '、'.join(data['on'])+small_separator
    else:
        comment += '-'+small_separator
    comment += '**Kunyomi:** '
    if len(data['kun']) > 0:
        comment += '、'.join(data['kun'])+small_separator
    else:
        comment += '-'+small_separator
    comment += '**Nanori:** '
    if len(data['nanori']) > 0:
        comment += '、'.join(data['nanori'])+big_separator
    else:
        comment += '-'+big_separator

    if not compact:
        misc_info = []
        if data['grade'] is not None:
            misc_info.append('**Grade:** '+str(data['grade']))
        if data['stroke_count'] is not None:
            misc_info.append('**Stroke Count:** '+str(data['stroke_count']))
        if data['frequency'] is not None:
            misc_info.append('**Frequency:** '+str(data['frequency']))
        if data['jlpt'] is not None:
            misc_info.append('**JLPT:** '+str(data['jlpt']))

        if len(misc_info) > 0:
            comment += ', '.join(misc_info)
            if compact:
                comment += '  \n'
            else:
                comment += '\n\n'

    parts_info = []
    if data['radical'] is not None:
        parts_info.append('**Radical:** '+data['radical'])
    if len(data['components']) > 0:
        parts_info.append('**Components:** '+' '.join(data['components']))
    comment += ' '.join(parts_info)

    img = get_stroke_image_url(kanji)
    if img is not None:
        if compact:
            comment += ' '
        else:
            comment += '\n\n'
        comment += '[Stroke Order]('+img+')'

    return comment


def get_word_info(word):
    '''
    Returns a markdown block with information about the specified kanji.
    '''

    data = db.get_word_data(word)

    comments = []
    for word in data:
        comment = '##'+word['word']+'\n\n'

        if word['alt_wording']:
            comment += '**Alternate form:** '
            comment += '、'.join(w['text'] for w in word['alt_wording'])+'\n\n'

        if word['reading']:
            comment += '**Reading:** '
            comment += '、'.join(w['text'] for w in word['reading'])+'\n\n'

        count = 1
        for m in word['meaning']:
            if m['gloss']:
                comment += str(count)+'. '+', '.join(m['gloss'])
                count += 1
                if m['misc']:
                    comment += '  \n_('+', '.join(m['misc'])+')_'

        comments.append(comment)

    return '\n\n---\n\n'.join(comments)


def reply_to_mentions():
    ''' Continuously reads reddit mentions and replies to them. '''

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
