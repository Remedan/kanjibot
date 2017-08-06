# Kanjibot 

A simple reddit bot that will reply with kanji information when called. To summon the bot, simply mention its name along with some kanji on the same line.

For example:

    Let's see some kanji info!
    /u/kanji-bot 桜 酒

## Dictionary Data

This bot uses the [KANJIDIC](http://nihongo.monash.edu/kanjidic2/index.html) and [KRADFILE](http://nihongo.monash.edu//kradinf.html) dictionary files. These files are the property of the [Electronic Dictionary Research and Development Group](http://www.edrdg.org/), and are used in conformance with the Group's [licence](http://www.edrdg.org/edrdg/licence.html).

## Stroke Order Images

The bot posts stroke order images when available. The source images come from the [KanjiVG project](http://kanjivg.tagaini.net/). The images are colorized using [KanjiColorizer](https://github.com/cayennes/kanji-colorize). Finally, I used [Inkscape](https://inkscape.org/) to convert them from svg to png.

The images should be placed in `jp-data/strokes`.
