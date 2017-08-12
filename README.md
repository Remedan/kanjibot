# Kanjibot 

A simple Reddit bot that will reply with kanji information when called.

## Usage

To summon the bot, simply mention its name along with some kanji on the same line.

For example:

    Let's see some kanji info!
    /u/kanji-bot 桜 酒

## Running the Code

Kanjibot needs a MySQL database to store its data. Before starting it you need to edit `praw.ini` and `kanjibot.ini` and fill in Reddit, Imgur and db info. If you want the bot to post stroke order images, you need to obtain them as described [below](#stroke-order-images) and place them in `jp-data/strokes`.

To fill the database with the data the bot needs, run:

    python -m kanjibot --init-db

_(Note: There are a few obscure characters that will fail to import into even utf8mb4 encoded table. I'm currently not sure what to do about this but it's not really a big issue.)_

To start the bot, run:

    python -m kanjibot

The bot will continuously read its inbox and post replies. I recommend creating a simple systemd (or equivalent) service to daemonize it.

## Future Plans

* ability to recognize words, not just kanji
* add 'words that this kanji is a part of'
* links to relevant dictionaries/websites

## Dictionary Data

This bot uses the [KANJIDIC](http://nihongo.monash.edu/kanjidic2/index.html) and [KRADFILE](http://nihongo.monash.edu//kradinf.html) dictionary files. These files are the property of the [Electronic Dictionary Research and Development Group](http://www.edrdg.org/), and are used in conformance with the Group's [licence](http://www.edrdg.org/edrdg/licence.html).

## Stroke Order Images

The bot posts stroke order images when available. The source images come from the [KanjiVG project](http://kanjivg.tagaini.net/). The images were colorized using [KanjiColorizer](https://github.com/cayennes/kanji-colorize). Finally, [Inkscape](https://inkscape.org/) was used to convert them from svg to png.

The images should be placed in `jp-data/strokes`. I didn't include them in the repo to save space.
