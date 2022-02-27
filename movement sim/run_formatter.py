import os
import sys
sys.path.extend((os.path.abspath('..\\resources\\packages'), os.getcwd()))

import input_formatter


def main():
    input_formatter.main()


if __name__ == '__main__':
    main()
