import time

import clipboard
import yaml


def main():
    # this is used to convert from a list of input tuples (e.g. [[2, 'r'], [4, 'l'], [3, '']]) to something that can just be pasted into studio
    # just copy a list from results.txt and it'll automatically become converted in your clipboard

    print('Auto formatter ready\n')

    while True:
        in_text_raw: str = clipboard.paste()
        in_text = in_text_raw.strip()

        if in_text.startswith('[[') and in_text.endswith(']]') and in_text.count('\'') > 1 and in_text.count('\'') % 2 == 0:  # that's probably good
            with open('config.yaml', 'r') as config_file:
                append_keys = yaml.safe_load(config_file)['append_keys']

            out = []

            for line in in_text.split('[')[2:]:
                line_split = line.split(',')
                out.append(line_split[0] + ' ' + line_split[1][2].replace('\'', '') + append_keys)

            out_joined = '\n'.join(out)

            if out_joined != in_text:
                print(in_text_raw.strip())
                print(out_joined)
                print()
                clipboard.copy(out_joined)

        time.sleep(0.5)


if __name__ == '__main__':
    main()
