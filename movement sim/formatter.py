import time

import clipboard
import yaml


def main():
    # this is used to convert from a list of input tuples (e.g. [(2, 'r'), (4, 'l'), (3, '')]) to something that can just be pasted into studio
    # just copy a list from out.txt and it'll automatically become converted in your clipboard

    with open('config.yaml', 'r') as config_file:
        append_keys = yaml.safe_load(config_file)['append_keys']

    print('\nauto formatter ready\n')

    while True:
        in_text: str = clipboard.paste().strip()
        print(in_text)
        in_text = in_text.replace(')))', '))').replace('((', '))')

        if in_text.count('(') > 0 and in_text.count(')') > 0 and in_text.count(',') % 2 == 1 and in_text.count('\'') % 2 == 0:  # that's probably good
            out = []

            for line in in_text.split('(')[1:]:
                line_split = line.split(',')
                out.append(line_split[0] + ' ' + line_split[1][2].replace('\'', '') + append_keys)

            out_joined = '\n'.join(out)
            print(out_joined)
            print()
            clipboard.copy(out_joined)

        time.sleep(0.5)


if __name__ == '__main__':
    main()
