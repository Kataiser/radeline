import os
import sys
sys.path.extend((os.path.abspath('..\\resources'), os.path.abspath('..\\resources\\packages'), os.getcwd()))

try:
    import sim_compiled as sim
except ImportError:
    import sim


def main():
    sim.main()


if __name__ == '__main__':
    main()
