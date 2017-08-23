import sys
from kanjibot import core


def main(argv):
    if '--init-db' in argv:
        core.init_database()
    else:
        while True:
            try:
                core.reply_to_mentions()
            except Exception as e:
                print(e)
                time.sleep(10)


if __name__ == '__main__':
    sys.exit(main(sys.argv))
