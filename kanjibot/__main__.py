import sys
from kanjibot import core


def main(argv):
    if '--init-db' in argv:
        core.init_database()
    else:
        core.reply_to_mentions()


if __name__ == '__main__':
    sys.exit(main(sys.argv))
