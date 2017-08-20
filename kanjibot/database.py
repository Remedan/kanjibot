
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

import xml.etree.ElementTree as ET
import mysql.connector


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
                '  `radical` char(1) NOT NULL,'
                '  PRIMARY KEY (`radical_id`),'
                '  UNIQUE KEY `radical` (`radical`)'
                ') ENGINE=InnoDB DEFAULT CHARSET=utf8mb4'
                ' COLLATE=utf8mb4_unicode_ci;'
            ),
            (
                'CREATE TABLE `kanji` ('
                '  `kanji_id` int(11) NOT NULL AUTO_INCREMENT,'
                '  `character` char(1) NOT NULL,'
                '  `radical_id` int(11) DEFAULT NULL,'
                '  `grade` int(11) DEFAULT NULL,'
                '  `stroke_count` int(11) DEFAULT NULL,'
                '  `frequency` int(11) DEFAULT NULL,'
                '  `jlpt_level` int(11) DEFAULT NULL,'
                '  PRIMARY KEY (`kanji_id`),'
                '  UNIQUE KEY `character` (`character`),'
                '  KEY `radical_id` (`radical_id`),'
                '  CONSTRAINT `kanji_ibfk_2` FOREIGN KEY (`radical_id`)'
                '  REFERENCES `kanji_radical` (`radical_id`) ON UPDATE CASCADE'
                ') ENGINE=InnoDB DEFAULT CHARSET=utf8mb4'
                ' COLLATE=utf8mb4_unicode_ci;'
            ),
            (
                'CREATE TABLE `kanji_component` ('
                '  `kanji_id` int(11) NOT NULL,'
                '  `character` char(1) NOT NULL,'
                '  KEY `kanji_id` (`kanji_id`),'
                '  CONSTRAINT `kanji_component_ibfk_2` FOREIGN KEY'
                '  (`kanji_id`) REFERENCES `kanji` (`kanji_id`)'
                '  ON DELETE CASCADE ON UPDATE CASCADE'
                ') ENGINE=InnoDB DEFAULT CHARSET=utf8mb4'
                ' COLLATE=utf8mb4_unicode_ci;'
            ),
            (
                'CREATE TABLE `kanji_meaning` ('
                '  `kanji_id` int(11) NOT NULL,'
                '  `meaning` text NOT NULL,'
                '  KEY `kanji_id` (`kanji_id`),'
                '  CONSTRAINT `kanji_meaning_ibfk_2` FOREIGN KEY (`kanji_id`)'
                '  REFERENCES `kanji` (`kanji_id`)'
                '  ON DELETE CASCADE ON UPDATE CASCADE'
                ') ENGINE=InnoDB DEFAULT CHARSET=utf8mb4'
                ' COLLATE=utf8mb4_unicode_ci;'
            ),
            (
                'CREATE TABLE `kanji_reading` ('
                '  `kanji_id` int(11) NOT NULL,'
                '  `reading` text NOT NULL,'
                '  `type` int(1) NOT NULL,'
                '  KEY `kanji_id` (`kanji_id`),'
                '  CONSTRAINT `kanji_reading_ibfk_1` FOREIGN KEY (`kanji_id`)'
                '  REFERENCES `kanji` (`kanji_id`)'
                '  ON DELETE CASCADE ON UPDATE CASCADE'
                ') ENGINE=InnoDB DEFAULT CHARSET=utf8mb4'
                ' COLLATE=utf8mb4_unicode_ci;'
            ),
            (
                'CREATE TABLE `word_entry` ('
                '  `word_entry_id` int(11) NOT NULL AUTO_INCREMENT,'
                '  `sequence_number` int(11) NOT NULL,'
                '  PRIMARY KEY (`word_entry_id`)'
                ') ENGINE=InnoDB DEFAULT CHARSET=utf8mb4'
                ' COLLATE=utf8mb4_unicode_ci;'
            ),
            (
                'CREATE TABLE `word_entry_wording` ('
                '  `wew_id` int(11) NOT NULL AUTO_INCREMENT,'
                '  `word_entry_id` int(11) NOT NULL,'
                '  `text` text COLLATE utf8mb4_unicode_ci NOT NULL,'
                '  PRIMARY KEY (`wew_id`),'
                '  KEY `word_entry_id` (`word_entry_id`),'
                '  CONSTRAINT `word_entry_wording_ibfk_2`'
                '  FOREIGN KEY (`word_entry_id`)'
                '  REFERENCES `word_entry` (`word_entry_id`)'
                '  ON DELETE CASCADE ON UPDATE CASCADE'
                ') ENGINE=InnoDB DEFAULT CHARSET=utf8mb4'
                ' COLLATE=utf8mb4_unicode_ci;'
            ),
            (
                'CREATE TABLE `wew_info` ('
                '  `wew_id` int(11) NOT NULL,'
                '  `text` text COLLATE utf8mb4_unicode_ci NOT NULL,'
                '  KEY `wew_id` (`wew_id`),'
                '  CONSTRAINT `wew_info_ibfk_3` FOREIGN KEY (`wew_id`)'
                '  REFERENCES `word_entry_wording` (`wew_id`)'
                '  ON DELETE CASCADE ON UPDATE CASCADE'
                ') ENGINE=InnoDB DEFAULT CHARSET=utf8mb4'
                ' COLLATE=utf8mb4_unicode_ci;'
            ),
            (
                'CREATE TABLE `word_entry_reading` ('
                '  `wer_id` int(11) NOT NULL AUTO_INCREMENT,'
                '  `word_entry_id` int(11) NOT NULL,'
                '  `reading` text COLLATE utf8mb4_unicode_ci NOT NULL,'
                '  PRIMARY KEY (`wer_id`),'
                '  KEY `word_entry_id` (`word_entry_id`),'
                '  CONSTRAINT `word_entry_reading_ibfk_2`'
                '  FOREIGN KEY (`word_entry_id`)'
                '  REFERENCES `word_entry` (`word_entry_id`)'
                '  ON DELETE CASCADE ON UPDATE CASCADE'
                ') ENGINE=InnoDB DEFAULT CHARSET=utf8mb4'
                ' COLLATE=utf8mb4_unicode_ci;'
            ),
            (
                'CREATE TABLE `wer_info` ('
                '  `wer_id` int(11) NOT NULL,'
                '  `text` text COLLATE utf8mb4_unicode_ci NOT NULL,'
                '  KEY `wer_id` (`wer_id`),'
                '  CONSTRAINT `wer_info_ibfk_2` FOREIGN KEY (`wer_id`)'
                '  REFERENCES `word_entry_reading` (`wer_id`)'
                '  ON DELETE CASCADE ON UPDATE CASCADE'
                ') ENGINE=InnoDB DEFAULT CHARSET=utf8mb4'
                ' COLLATE=utf8mb4_unicode_ci;'
            ),
            (
                'CREATE TABLE `word_entry_meaning` ('
                '  `wem_id` int(11) NOT NULL AUTO_INCREMENT,'
                '  `word_entry_id` int(11) NOT NULL,'
                '  PRIMARY KEY (`wem_id`),'
                '  KEY `word_entry_id` (`word_entry_id`),'
                '  CONSTRAINT `word_entry_meaning_ibfk_2`'
                '  FOREIGN KEY (`word_entry_id`)'
                '  REFERENCES `word_entry` (`word_entry_id`)'
                '  ON DELETE CASCADE ON UPDATE CASCADE'
                ') ENGINE=InnoDB DEFAULT CHARSET=utf8mb4'
                ' COLLATE=utf8mb4_unicode_ci;'
            ),
            (
                'CREATE TABLE `wem_field` ('
                '  `wem_id` int(11) NOT NULL,'
                '  `field` text COLLATE utf8mb4_unicode_ci NOT NULL,'
                '  KEY `wem_id` (`wem_id`),'
                '  CONSTRAINT `wem_field_ibfk_2` FOREIGN KEY (`wem_id`)'
                '  REFERENCES `word_entry_meaning` (`wem_id`)'
                '  ON DELETE CASCADE ON UPDATE CASCADE'
                ') ENGINE=InnoDB DEFAULT CHARSET=utf8mb4'
                ' COLLATE=utf8mb4_unicode_ci;'
            ),
            (
                'CREATE TABLE `wem_gloss` ('
                '  `wem_id` int(11) NOT NULL,'
                '  `text` text COLLATE utf8mb4_unicode_ci NOT NULL,'
                '  KEY `wem_id` (`wem_id`),'
                '  CONSTRAINT `wem_gloss_ibfk_2` FOREIGN KEY (`wem_id`)'
                '  REFERENCES `word_entry_meaning` (`wem_id`)'
                '  ON DELETE CASCADE ON UPDATE CASCADE'
                ') ENGINE=InnoDB DEFAULT CHARSET=utf8mb4'
                ' COLLATE=utf8mb4_unicode_ci;'
            ),
            (
                'CREATE TABLE `wem_misc` ('
                '  `wem_id` int(11) NOT NULL,'
                '  `text` text COLLATE utf8mb4_unicode_ci NOT NULL,'
                '  KEY `wem_id` (`wem_id`),'
                '  CONSTRAINT `wem_misc_ibfk_2` FOREIGN KEY (`wem_id`)'
                '  REFERENCES `word_entry_meaning` (`wem_id`)'
                '  ON DELETE CASCADE ON UPDATE CASCADE'
                ') ENGINE=InnoDB DEFAULT CHARSET=utf8mb4'
                ' COLLATE=utf8mb4_unicode_ci;'
            ),
            (
                'CREATE TABLE `wem_part_of_speech` ('
                '  `wem_id` int(11) NOT NULL,'
                '  `text` text COLLATE utf8mb4_unicode_ci NOT NULL,'
                '  KEY `wem_id` (`wem_id`),'
                '  CONSTRAINT `wem_part_of_speech_ibfk_2`'
                '  FOREIGN KEY (`wem_id`)'
                '  REFERENCES `word_entry_meaning` (`wem_id`)'
                '  ON DELETE CASCADE ON UPDATE CASCADE'
                ') ENGINE=InnoDB DEFAULT CHARSET=utf8mb4'
                ' COLLATE=utf8mb4_unicode_ci;'
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
                    'INSERT INTO `kanji_radical` (`radical`)'
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
                    '  `character`,'
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
                    '(`kanji_id`, `meaning`)'
                    'VALUES (%s, %s)',
                    (kanji_id, m)
                )
            for o in on:
                cursor.execute(
                    'INSERT INTO `kanji_reading`'
                    '(`kanji_id`, `reading`, `type`)'
                    'VALUES (%s, %s, 0)',
                    (kanji_id, o)
                )
            for k in kun:
                cursor.execute(
                    'INSERT INTO `kanji_reading`'
                    '(`kanji_id`, `reading`, `type`)'
                    'VALUES (%s, %s, 1)',
                    (kanji_id, k)
                )
            for n in nanori:
                cursor.execute(
                    'INSERT INTO `kanji_reading`'
                    '(`kanji_id`, `reading`, `type`)'
                    'VALUES (%s, %s, 2)',
                    (kanji_id, n)
                )
            if literal in components:
                for c in components[literal]:
                    cursor.execute(
                        'INSERT INTO `kanji_component`'
                        '(`kanji_id`, `character`)'
                        'VALUES (%s, %s)',
                        (kanji_id, c)
                    )

            self.cnx.commit()

        cursor.close()

    def _load_words(self):
        tree = ET.parse('jp-data/JMdict_e')
        word_data = tree.getroot()

        cursor = self._get_cursor()
        for entry in word_data.iter('entry'):
            seq = entry.find('ent_seq').text
            cursor.execute(
                'INSERT INTO `word_entry` (`sequence_number`)'
                'VALUES (%s)',
                (seq,)
            )
            entry_id = cursor.lastrowid
            for k in entry.iter('k_ele'):
                wording = k.find('keb').text
                cursor.execute(
                    'INSERT INTO `word_entry_wording`'
                    '(`word_entry_id`, `text`)'
                    'VALUES (%s, %s)',
                    (entry_id, wording)
                )
                wording_id = cursor.lastrowid
                for info in k.iter('ke_inf'):
                    cursor.execute(
                        'INSERT INTO `wew_info`'
                        '(`wew_id`, `text`)'
                        'VALUES (%s, %s)',
                        (wording_id, info.text)
                    )
            for r in entry.iter('r_ele'):
                reading = r.find('reb').text
                cursor.execute(
                    'INSERT INTO `word_entry_reading`'
                    '(`word_entry_id`, `reading`)'
                    'VALUES (%s, %s)',
                    (entry_id, reading)
                )
                reading_id = cursor.lastrowid
                for info in r.iter('re_inf'):
                    cursor.execute(
                        'INSERT INTO `wer_info`'
                        '(`wer_id`, `text`)'
                        'VALUES (%s, %s)',
                        (reading_id, info.text)
                    )
            for sense in entry.iter('sense'):
                cursor.execute(
                    'INSERT INTO `word_entry_meaning`'
                    '(`word_entry_id`)'
                    'VALUES (%s)',
                    (entry_id,)
                )
                meaning_id = cursor.lastrowid
                for pos in sense.iter('pos'):
                    cursor.execute(
                        'INSERT INTO `wem_part_of_speech`'
                        '(`wem_id`, `text`)'
                        'VALUES (%s, %s)',
                        (meaning_id, pos.text)
                    )
                for field in sense.iter('field'):
                    cursor.execute(
                        'INSERT INTO `wem_field`'
                        '(`wem_id`, `field`)'
                        'VALUES (%s, %s)',
                        (meaning_id, field.text)
                    )
                for misc in sense.iter('misc'):
                    cursor.execute(
                        'INSERT INTO `wem_misc`'
                        '(`wem_id`, `text`)'
                        'VALUES (%s, %s)',
                        (meaning_id, misc.text)
                    )
                for gloss in sense.iter('gloss'):
                    cursor.execute(
                        'INSERT INTO `wem_gloss`'
                        '(`wem_id`, `text`)'
                        'VALUES (%s, %s)',
                        (meaning_id, gloss.text)
                    )

            self.cnx.commit()
        cursor.close()

    def fill_database(self):
        ''' Fills an empty database with language data. '''

        self._create_tables()
        self._load_radicals()
        self._load_kanji()
        self._load_words()

    def get_kanji_data(self, kanji):
        ''' Returns a dict with info about a kanji. '''

        cursor = self._get_cursor()
        cursor.execute(
            'SELECT `kanji_id`, `character`, `grade`, `stroke_count`,'
            '       `frequency`, `jlpt_level`, `radical`'
            'FROM `kanji` LEFT JOIN `kanji_radical` USING (`radical_id`)'
            'WHERE `character` = %s',
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
            'SELECT `meaning` FROM `kanji_meaning`'
            'WHERE `kanji_id` = %s',
            (kanji_id,)
        )
        data['meaning'] = [row[0] for row in cursor]
        cursor.execute(
            'SELECT `reading` FROM `kanji_reading`'
            'WHERE `type` = 0 AND `kanji_id` = %s',
            (kanji_id,)
        )
        data['on'] = [row[0] for row in cursor]
        cursor.execute(
            'SELECT `reading` FROM `kanji_reading`'
            'WHERE `type` = 1 AND `kanji_id` = %s',
            (kanji_id,)
        )
        data['kun'] = [row[0] for row in cursor]
        cursor.execute(
            'SELECT `reading` FROM `kanji_reading`'
            'WHERE `type` = 2 AND `kanji_id` = %s',
            (kanji_id,)
        )
        data['nanori'] = [row[0] for row in cursor]
        cursor.execute(
            'SELECT `character` FROM `kanji_component`'
            'WHERE `kanji_id` = %s',
            (kanji_id,)
        )
        data['components'] = [row[0] for row in cursor]

        cursor.close()
        return data

    def get_word_data(self, word):
        cursor = self._get_cursor()
        cursor.execute(
            'SELECT `word_entry_id`'
            ' FROM `word_entry`'
            ' JOIN `word_entry_wording` USING (`word_entry_id`)'
            ' WHERE `text` = %s',
            (word,)
        )
        rows = list(cursor)
        if not rows:
            return None

        data = []
        for w in rows:
            word_data = {'word': word}
            entry_id = w[0]
            cursor.execute(
                'SELECT `wew_id`, `text` FROM `word_entry_wording`'
                ' WHERE `word_entry_id` = %s',
                (entry_id,)
            )
            word_data['alt_wording'] = []
            for alt in list(cursor):
                if alt[1] != word:
                    alt_wording = {'text': alt[1]}
                    cursor.execute(
                        'SELECT `text` FROM `wew_info`'
                        'WHERE `wew_id` = %s',
                        (alt[0],)
                    )
                    alt_wording['info'] = [row[0] for row in cursor]
                    word_data['alt_wording'].append(alt_wording)

            cursor.execute(
                'SELECT `wer_id`, `reading` FROM `word_entry_reading`'
                ' WHERE `word_entry_id` = %s',
                (entry_id,)
            )
            word_data['reading'] = []
            for r in list(cursor):
                reading = {'text': r[1]}
                cursor.execute(
                    'SELECT `text` FROM `wer_info`'
                    'WHERE `wer_id` = %s',
                    (r[0],)
                )
                reading['info'] = [row[0] for row in cursor]
                word_data['reading'].append(reading)

            cursor.execute(
                'SELECT `wem_id` FROM `word_entry_meaning`'
                ' WHERE `word_entry_id` = %s',
                (entry_id,)
            )
            word_data['meaning'] = []
            for m in list(cursor):
                meaning = {}
                cursor.execute(
                    'SELECT `text` FROM `wem_part_of_speech`'
                    'WHERE `wem_id` = %s',
                    (m[0],)
                )
                meaning['pos'] = [row[0] for row in cursor]
                cursor.execute(
                    'SELECT `field` FROM `wem_field`'
                    'WHERE `wem_id` = %s',
                    (m[0],)
                )
                meaning['field'] = [row[0] for row in cursor]
                cursor.execute(
                    'SELECT `text` FROM `wem_gloss`'
                    'WHERE `wem_id` = %s',
                    (m[0],)
                )
                meaning['gloss'] = [row[0] for row in cursor]
                cursor.execute(
                    'SELECT `text` FROM `wem_misc`'
                    'WHERE `wem_id` = %s',
                    (m[0],)
                )
                meaning['misc'] = [row[0] for row in cursor]
                word_data['meaning'].append(meaning)

            data.append(word_data)

        cursor.close()
        return data
