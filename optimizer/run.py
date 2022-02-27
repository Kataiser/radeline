import os
import sys
sys.path.extend((os.path.abspath('..'), os.path.abspath('..\\packages'), os.getcwd()))

import main as optimizer


def main():
    optimizer.main()


if __name__ == '__main__':
    main()
