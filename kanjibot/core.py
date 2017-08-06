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

import praw
import base64
import requests
import json
import configparser
import os.path
import xml.etree.ElementTree as ET


config = None
kanji_data = None
radicals = {}


def load_kanji_data():
    ''' Loads dictionary data into memory. '''

    print('Reading kanjidic2.xml... ', end='')
    tree = ET.parse('jp-data/kanjidic2.xml')
    global kanji_data
    kanji_data = tree.getroot()
    print('done')
    print('Reading kradfile... ', end='')
    with open('jp-data/kradfile', 'r') as f:
        for line in f:
            parts = line[:-1].split(' ')
            radicals[parts[0]] = parts[2:]
    print('done')
    print('Reading kradfile2... ', end='')
    with open('jp-data/kradfile2', 'r') as f:
        for line in f:
            parts = line[:-1].split(' ')
            radicals[parts[0]] = parts[2:]
    print('done')
    pass


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


def get_stroke_image_url(kanji):
    ''' Uploads kanji stroke order image to imgur and returns its url. '''

    path = 'jp-data/strokes/'+kanji+'.png'
    if os.path.isfile(path):
        with open(path, 'rb') as f:
            client_id = config['kanji-bot']['imgur_id']
            url = 'https://api.imgur.com/3/image'
            img = f.read()
            img_base64 = base64.b64encode(img)
            response = requests.post(
                url,
                headers={'Authorization': 'Client-ID '+client_id},
                data={
                    'image': img_base64,
                    'type': 'base64',
                    'title': kanji+' stroke order'
                }
            )
            response_data = json.loads(response.text)
            if response_data['success']:
                return response_data['data']['link']
            else:
                print('Imgur upload failed!')
                return None
    else:
        return None


def get_kanji_info(kanji):
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
        return '#Couldn\'t find data for kanji \''+kanji+'\''

    comment = '#'+kanji+'\n\n'

    rm = data.find('reading_meaning')
    comment += '**Meaning:** '
    meanings = []
    for meaning in rm.iter('meaning'):
        if 'm_lang' not in meaning.attrib:
            meanings.append(meaning.text)
    comment += ', '.join(meanings)+'\n\n'

    comment += '**Onyomi:** '
    on = []
    for reading in rm.iter('reading'):
        if reading.attrib['r_type'] == 'ja_on':
            on.append(reading.text)
    comment += '、'.join(on)+'  \n'
    comment += '**Kunyomi:** '
    kun = []
    for reading in rm.iter('reading'):
        if reading.attrib['r_type'] == 'ja_kun':
            kun.append(reading.text)
    comment += '、'.join(kun)+'  \n'
    comment += 'Nanori: '
    nanori = []
    for reading in rm.iter('nanori'):
        nanori.append(reading.text)
    comment += '、'.join(nanori)+'\n\n'

    misc = data.find('misc')
    comment += '**Grade:** '+misc.find('grade').text
    comment += ',  **Stroke Count:** '+misc.find('stroke_count').text
    comment += ',  **Frequncy:** '+misc.find('freq').text
    comment += ',  **JLPT:** '+misc.find('jlpt').text

    if kanji in radicals:
        comment += '\n\n**Radicals:** '
        for rad in radicals[kanji]:
            comment += rad+' '
        comment = comment[:-2]

    img = get_stroke_image_url(kanji)
    if img is not None:
        comment += '\n\n[Stroke Order]('+img+')'

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
        print(
            'Reading mention by /u/'+mention.author.name,
            'in /r/'+mention.subreddit.display_name
        )
        for line in mention.body.split('\n'):
            if '/u/'+account in line:
                kanji = extract_kanji(line)
                if len(kanji) > 0:
                    print('Found kanji:', ' '.join(kanji))
                    print('Sending response...', end='')
                    reply = [get_kanji_info(k) for k in kanji]
                    comment = '\n\n---\n\n'.join(reply)
                    comment += '\n\n---\n\n'+footer
                    mention.reply(comment)
                    print(' done')
                    break
                else:
                    print(' no kanji found')
        mention.mark_read()
