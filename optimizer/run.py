import os
import sys
sys.path.extend((os.path.abspath('..\\resources'), os.path.abspath('..\\resources\\packages'), os.getcwd()))

import main as optimizer


def main():
    optimizer.main()


if __name__ == '__main__':
    main()
