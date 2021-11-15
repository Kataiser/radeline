import time

import pyperclip
import yaml


def main():
    # this is used to convert from a list of input tuples (e.g. [[2, 'r'], [4, 'l'], [3, '']]) to something that can just be pasted into studio
    # just copy a list from results.txt and it'll automatically become converted in your clipboard

    print('Auto formatter ready\n')

    while True:
        in_text: str = pyperclip.paste().strip()

        if in_text.startswith('[[') and in_text.endswith(']]') and in_text.count('\'') > 1 and in_text.count('\'') % 2 == 0:  # that's probably good
            with open('config.yaml', 'r') as config_file:
                append_keys_config = yaml.safe_load(config_file)['append_keys']

            append_keys = '' if append_keys_config is None else append_keys_config.replace(' ', '')
            out = []

            for line in in_text.split('[')[2:]:
                line_split = line.split(',')
                frame_count = line_split[0]
                key_held = line_split[1][2].replace('\'', '')
                assert frame_count not in (None, '')
                assert key_held is not None
                out.append(frame_count + ' ' + key_held + append_keys)

            assert out
            out_joined = '\n'.join(out)
            assert out_joined

            if out_joined != in_text:
                print(in_text)
                print(out_joined)
                print()
                pyperclip.copy(out_joined)

        time.sleep(0.5)


if __name__ == '__main__':
    main()
