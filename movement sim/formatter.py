import time

import clipboard


def main():
    # this is used to convert from a list of input tuples (e.g. [(2, 'r'), (4, 'l'), (3, '')]) to something that can just be pasted into studio
    # just copy a list from out.txt and it'll automatically become converted in your clipboard

    print('ready\n')

    while True:
        in_text: str = clipboard.paste()

        if in_text.count('[') == 1 and in_text.count(']') == 1 and in_text.count('(') > 0 and in_text.count('(') == in_text.count(')'):
            out = []

            for line in in_text.split('(')[1:]:
                out.append(line[0] + line[4].replace('\'', ''))

            out_joined = '\n'.join(out)
            print(out_joined)
            print()
            clipboard.copy(out_joined)

        time.sleep(0.5)


if __name__ == '__main__':
    main()
