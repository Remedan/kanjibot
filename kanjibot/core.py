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
import mysql.connector
from io import BytesIO
from collections import OrderedDict
from PIL import Image
from PIL import ImageDraw
from PIL import ImageFont


class Database:
    '''
    This class is used to import and retrieve language data to/from the db.
    '''

    def __init__(self, host, db_name, user, password):
        try:
            self.cnx = mysql.connector.connect(
                user=user,
                password=password,
                host=host,
                database=db_name,
                use_unicode=True,
                charset='utf8mb4'
            )
        except mysql.connector.Error as err:
            print(err)

    def __del__(self):
        self.cnx.close()

    def _get_cursor(self):
        cursor = self.cnx.cursor()
        cursor.execute('SET NAMES utf8mb4')
        cursor.execute("SET CHARACTER SET utf8mb4")
        cursor.execute("SET character_set_connection=utf8mb4")

        return cursor

    def _create_tables(self):
        tables = [
            (
                'CREATE TABLE `kanji_radical` ('
                '  `radical_id` int(11) NOT NULL AUTO_INCREMENT,'
                '  `radical_character` char(1) NOT NULL,'
                '  PRIMARY KEY (`radical_id`),'
                '  UNIQUE KEY `radical_character` (`radical_character`)'
                ') ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;'
            ),
            (
                'CREATE TABLE `kanji` ('
                '  `kanji_id` int(11) NOT NULL AUTO_INCREMENT,'
                '  `kanji_character` char(1) NOT NULL,'
                '  `radical_id` int(11) DEFAULT NULL,'
                '  `grade` int(11) DEFAULT NULL,'
                '  `stroke_count` int(11) DEFAULT NULL,'
                '  `frequency` int(11) DEFAULT NULL,'
                '  `jlpt_level` int(11) DEFAULT NULL,'
                '  PRIMARY KEY (`kanji_id`),'
                '  UNIQUE KEY `kanji_character` (`kanji_character`),'
                '  KEY `radical_id` (`radical_id`),'
                '  CONSTRAINT `kanji_ibfk_2` FOREIGN KEY (`radical_id`)'
                '  REFERENCES `kanji_radical` (`radical_id`) ON UPDATE CASCADE'
                ') ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;'
            ),
            (
                'CREATE TABLE `kanji_component` ('
                '  `kanji_id` int(11) NOT NULL,'
                '  `component_character` char(1) NOT NULL,'
                '  KEY `kanji_id` (`kanji_id`),'
                '  CONSTRAINT `kanji_component_ibfk_2` FOREIGN KEY'
                '  (`kanji_id`) REFERENCES `kanji` (`kanji_id`)'
                '  ON DELETE CASCADE ON UPDATE CASCADE'
                ') ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;'
            ),
            (
                'CREATE TABLE `kanji_meaning` ('
                '  `kanji_id` int(11) NOT NULL,'
                '  `meaning_text` text NOT NULL,'
                '  KEY `kanji_id` (`kanji_id`),'
                '  CONSTRAINT `kanji_meaning_ibfk_2` FOREIGN KEY (`kanji_id`)'
                '  REFERENCES `kanji` (`kanji_id`)'
                '  ON DELETE CASCADE ON UPDATE CASCADE'
                ') ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;'
            ),
            (
                'CREATE TABLE `kanji_reading` ('
                '  `kanji_id` int(11) NOT NULL,'
                '  `reading_text` text NOT NULL,'
                '  `reading_type` int(1) NOT NULL,'
                '  KEY `kanji_id` (`kanji_id`),'
                '  CONSTRAINT `kanji_reading_ibfk_1` FOREIGN KEY (`kanji_id`)'
                '  REFERENCES `kanji` (`kanji_id`)'
                ') ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;'
            )
        ]
        cursor = self._get_cursor()
        for table in tables:
            try:
                cursor.execute(table)
            except mysql.connector.Error as err:
                print(err)
        cursor.close()

    def _load_radicals(self):
        cursor = self._get_cursor()
        with open('jp-data/radicals', 'r') as f:
            for radical in f.read().strip():
                cursor.execute(
                    'INSERT INTO `kanji_radical` (`radical_character`)'
                    'VALUES (%s)',
                    (radical,)
                )
        self.cnx.commit()
        cursor.close()

    def _load_kanji(self):
        tree = ET.parse('jp-data/kanjidic2.xml')
        kanji_data = tree.getroot()
        components = {}
        with open('jp-data/kradfile', 'r') as f:
            for line in f:
                parts = line.strip().split(' ')
                components[parts[0]] = parts[2:]
        with open('jp-data/kradfile2', 'r') as f:
            for line in f:
                parts = line.strip().split(' ')
                components[parts[0]] = parts[2:]

        cursor = self._get_cursor()
        for kanji in kanji_data.iter('character'):
            literal = kanji.find('literal').text
            meanings = []
            for meaning in kanji.iter('meaning'):
                if 'm_lang' not in meaning.attrib:
                    meanings.append(meaning.text)
            on = []
            kun = []
            for reading in kanji.iter('reading'):
                if reading.attrib['r_type'] == 'ja_on':
                    on.append(reading.text)
                elif reading.attrib['r_type'] == 'ja_kun':
                    kun.append(reading.text)
            nanori = []
            for reading in kanji.iter('nanori'):
                nanori.append(reading.text)
            misc = kanji.find('misc')
            grade = misc.find('grade')
            if grade is not None:
                grade = int(grade.text)
            stroke_count = misc.find('stroke_count')
            if stroke_count is not None:
                stroke_count = int(stroke_count.text)
            frequency = misc.find('freq')
            if frequency is not None:
                frequency = int(frequency.text)
            jlpt = misc.find('jlpt')
            if jlpt is not None:
                jlpt = int(jlpt.text)
            radical = None
            for rv in kanji.find('radical').findall('rad_value'):
                if rv.attrib['rad_type'] == 'classical':
                    radical = int(rv.text)

            # TODO There are a few characters that even utf8mb4 can't store.
            #      I don't really know what to do about them.
            try:
                cursor.execute(
                    'INSERT INTO `kanji` ('
                    '  `kanji_character`,'
                    '  `radical_id`,'
                    '  `grade`,'
                    '  `stroke_count`,'
                    '  `frequency`,'
                    '  `jlpt_level`'
                    ') VALUES (%s, %s, %s, %s, %s, %s)',
                    (literal, radical, grade, stroke_count, frequency, jlpt)
                )
            except mysql.connector.Error as err:
                print('Error inserting data about \''+literal+'\':')
                print(err)
                continue

            kanji_id = cursor.lastrowid
            for m in meanings:
                cursor.execute(
                    'INSERT INTO `kanji_meaning`'
                    '(`kanji_id`, `meaning_text`)'
                    'VALUES (%s, %s)',
                    (kanji_id, m)
                )
            for o in on:
                cursor.execute(
                    'INSERT INTO `kanji_reading`'
                    '(`kanji_id`, `reading_text`, `reading_type`)'
                    'VALUES (%s, %s, 0)',
                    (kanji_id, o)
                )
            for k in kun:
                cursor.execute(
                    'INSERT INTO `kanji_reading`'
                    '(`kanji_id`, `reading_text`, `reading_type`)'
                    'VALUES (%s, %s, 1)',
                    (kanji_id, k)
                )
            for n in nanori:
                cursor.execute(
                    'INSERT INTO `kanji_reading`'
                    '(`kanji_id`, `reading_text`, `reading_type`)'
                    'VALUES (%s, %s, 2)',
                    (kanji_id, n)
                )
            if literal in components:
                for c in components[literal]:
                    cursor.execute(
                        'INSERT INTO `kanji_component`'
                        '(`kanji_id`, `component_character`)'
                        'VALUES (%s, %s)',
                        (kanji_id, c)
                    )

            self.cnx.commit()

        cursor.close()

    def fill_database(self):
        ''' Fills an empty database with language data. '''

        self._create_tables()
        self._load_radicals()
        self._load_kanji()

    def get_kanji_data(self, kanji):
        ''' Returns a dict with info about a kanji. '''

        cursor = self._get_cursor()
        cursor.execute(
            'SELECT `kanji_id`, `kanji_character`, `grade`, `stroke_count`,'
            '       `frequency`, `jlpt_level`, `radical_character`'
            'FROM `kanji` LEFT JOIN `kanji_radical` USING (`radical_id`)'
            'WHERE `kanji_character` = %s',
            (kanji,)
        )
        data = {}
        rows = list(cursor)
        if not rows:
            return None

        (
            kanji_id,
            data['literal'],
            data['grade'],
            data['stroke_count'],
            data['frequency'],
            data['jlpt'],
            data['radical']
        ) = rows[0]
        cursor.execute(
            'SELECT `meaning_text` FROM `kanji_meaning`'
            'WHERE `kanji_id` = %s',
            (kanji_id,)
        )
        data['meaning'] = [row[0] for row in cursor]
        cursor.execute(
            'SELECT `reading_text` FROM `kanji_reading`'
            'WHERE `reading_type` = 0 AND `kanji_id` = %s',
            (kanji_id,)
        )
        data['on'] = [row[0] for row in cursor]
        cursor.execute(
            'SELECT `reading_text` FROM `kanji_reading`'
            'WHERE `reading_type` = 1 AND `kanji_id` = %s',
            (kanji_id,)
        )
        data['kun'] = [row[0] for row in cursor]
        cursor.execute(
            'SELECT `reading_text` FROM `kanji_reading`'
            'WHERE `reading_type` = 2 AND `kanji_id` = %s',
            (kanji_id,)
        )
        data['nanori'] = [row[0] for row in cursor]
        cursor.execute(
            'SELECT `component_character` FROM `kanji_component`'
            'WHERE `kanji_id` = %s',
            (kanji_id,)
        )
        data['components'] = [row[0] for row in cursor]

        cursor.close()
        return data


config = configparser.ConfigParser()
config.read('kanjibot.ini')
db = Database(
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
