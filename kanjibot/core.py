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
import re
import requests
import praw
import prawcore
import urllib
from io import BytesIO
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


def is_kana(character):
    ''' https://stackoverflow.com/a/30070664 '''

    ranges = [
        {"from": ord(u"\u3040"), "to": ord(u"\u309f")},
        {"from": ord(u"\u30a0"), "to": ord(u"\u30ff")}
    ]

    return any(
        [range['from'] <= ord(character) <= range['to'] for range in ranges]
    )


def extract_kanji(string):
    ''' Returns a list of all kanji in a string. '''

    return list(filter(lambda c: is_kanji(c), string))


def contains_japanese(text):
    ''' Checks whether string contains japanese characters. '''

    return any(is_kanji(char) or is_kana(char) for char in text)


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


def get_kanji_search_links(kanji):
    links = '^^[\[jisho\]](http://jisho.org/search/'
    links += urllib.parse.quote_plus(kanji+'#kanji')+')'
    links += ' ^^[\[Wiktionary\]](http://en.wiktionary.org/wiki/'
    links += urllib.parse.quote_plus(kanji+'#Japanese')+')'
    links += ' ^^[\[Tatoeba\]](https://tatoeba.org/eng/sentences/'
    links += 'search?from=jpn&to=eng&query='
    links += urllib.parse.quote_plus(kanji)+')'
    links += ' ^^[\[alc\]](http://eow.alc.co.jp/search?q='
    links += urllib.parse.quote_plus(kanji)+')'
    links += ' ^^[\[Glosbe\]](https://glosbe.com/ja/en/'
    links += urllib.parse.quote_plus(kanji)+')'

    return links


def get_kanji_info(kanji):
    '''
    Returns a markdown block with information about the specified kanji.
    Will also upload a stroke order image to imgur.
    '''

    data = db.get_kanji_data(kanji)

    comment = '##['+kanji+']('+get_preview_image_url(kanji)+')'
    comment += ' '+get_kanji_search_links(kanji)+'\n\n'

    if data is None:
        return (
            '##Couldn\'t find data for kanji \''+kanji+'\'\n\n'
            + get_kanji_search_links(kanji)
        )

    comment += '**Meaning:** '
    comment += ', '.join(data['meaning'])+'  \n'

    comment += '**Onyomi:** '
    if len(data['on']) > 0:
        comment += '、'.join(data['on'])+' '
    else:
        comment += '- '
    comment += '**Kunyomi:** '
    if len(data['kun']) > 0:
        comment += '、'.join(data['kun'])+' '
    else:
        comment += '- '
    comment += '**Nanori:** '
    if len(data['nanori']) > 0:
        comment += '、'.join(data['nanori'])+'  \n'
    else:
        comment += '-  \n'

    parts_info = []
    if data['radical'] is not None:
        parts_info.append('**Radical:** '+data['radical'])
    if len(data['components']) > 0:
        parts_info.append('**Components:** '+' '.join(data['components']))
    comment += ' '.join(parts_info)

    img = get_stroke_image_url(kanji)
    if img is not None:
        comment += ' [Stroke Order]('+img+')'

    return comment


def get_word_search_links(word):
    links = '^^[\[jisho\]](http://jisho.org/search/'
    links += urllib.parse.quote_plus(word)+')'
    links += ' ^^[\[Wiktionary\]](http://en.wiktionary.org/wiki/'
    links += urllib.parse.quote_plus(word+'#Japanese')+')'
    links += ' ^^[\[Tatoeba\]](https://tatoeba.org/eng/sentences/'
    links += 'search?from=jpn&to=eng&query='
    links += urllib.parse.quote_plus(word)+')'
    links += ' ^^[\[alc\]](http://eow.alc.co.jp/search?q='
    links += urllib.parse.quote_plus(word)+')'
    links += ' ^^[\[Glosbe\]](https://glosbe.com/ja/en/'
    links += urllib.parse.quote_plus(word)+')'
    links += ' ^^[\[OJAD\]]('
    links += 'http://www.gavo.t.u-tokyo.ac.jp/ojad/search/index/word:'
    links += urllib.parse.quote_plus(word)+')'

    return links


def get_word_info(word):
    '''
    Returns a markdown block with information about the specified kanji.
    '''

    data = db.get_word_data(word)
    if data is None:
        return (
            '##Couldn\'t find data for word \''
            + word+'\'\n\n'+get_word_search_links(word)
        )

    comments = []
    for word in data:
        comment = '##'+word['word']
        comment += ' '+get_word_search_links(word['word'])+'\n\n'

        info = []
        if word['alt_wording']:
            wording_info = '**Alternate form:** '
            wording_info += '、'.join(
                w['text'] for w in word['alt_wording']
            )
            info.append(wording_info)

        readings = [
            r['text'] for r in word['reading'] if r['text'] != word['word']
        ]
        if readings:
            reading_info = '**Reading:** '
            reading_info += '、'.join(readings)
            info.append(reading_info)
        if info:
            comment += '  \n'.join(info)+'\n\n'

        count = 1
        for m in word['meaning']:
            if m['gloss']:
                comment += str(count)+'. '+', '.join(m['gloss'])
                count += 1
                if m['misc']:
                    comment += '  \n_('+', '.join(m['misc'])+')_'
                comment += '\n'

        comments.append(comment)

    return '\n\n---\n\n'.join(comments)


def parse_line(line):
    ''' Extracts kanji and words from a line of text. '''

    delimiters = '[\s,、]+'
    parts = re.split(delimiters, line)

    found = {'kanji': [], 'words': []}
    kanji_mode = False
    word_mode = False
    for word in parts:
        if not contains_japanese(word):
            if word == '!kanji':
                kanji_mode = True
                word_mode = False
            elif word == '!word' or word == '!words':
                word_mode = True
                kanji_mode = False
            continue

        if kanji_mode or (
                not word_mode and (not db.is_word(word) or len(word) == 1)
        ):
            found['kanji'] = found['kanji'] + extract_kanji(word)
        else:
            found['words'].append(word)

    return found


def reply_to_mentions():
    ''' Continuously reads reddit mentions and replies to them. '''

    account = config['kanji-bot']['reddit_account']
    footer = config['kanji-bot']['footer']
    reddit = praw.Reddit('kanji-bot')

    print('Connected to reddit, waiting for summons...')
    for mention in reddit.inbox.stream():
        for i in range(3):
            try:
                print('Reading mention by /u/'+mention.author.name, end='')
                if hasattr(mention.subreddit, 'display_name'):
                    print(' in /r/'+mention.subreddit.display_name)
                else:
                    print()
                for line in mention.body.split('\n'):
                    if 'u/'+account in line:
                        found = parse_line(line)
                        if found['kanji'] or found['words']:
                            print('Sending response...', end='')
                            info = [get_kanji_info(k) for k in found['kanji']]
                            info += [get_word_info(w) for w in found['words']]
                            comment = '\n\n---\n\n'.join(info)
                            comment += '\n\n---\n\n'+footer
                            mention.reply(comment)
                            print(' done')
                        else:
                            print('No kanji found')
                break
            except prawcore.exceptions.RequestException as e:
                print(e)

        mention.mark_read()
