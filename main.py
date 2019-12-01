import os
import random
import time

import keyboard
from bs4 import BeautifulSoup


def main():
    celeste_path = r'C:\Program Files (x86)\Steam\steamapps\common\Celeste'
    failed_lines = []

    print_and_log("Starting in 3 seconds, switch to the Celeste window!")
    time.sleep(3)

    print_and_log("Getting reference data")
    run_tas()

    save_data = get_current_session(os.path.join(celeste_path, 'saves', 'debug.celeste'))
    target_time = og_target_time = int(save_data['time'])
    target_level = save_data['level']
    print_and_log(f"Target time is {target_time} in level {target_level}")

    while True:
        with open(os.path.join(celeste_path, 'Celeste.tas'), 'r') as celeste_tas_file_read:
            celeste_tas = celeste_tas_file_read.readlines()

        valid_line = False
        while not valid_line:
            line_num = random.randint(7, len(celeste_tas) - 1)
            original_line = celeste_tas[line_num]
            line = original_line.lstrip(' ').rstrip('\n')

            if ',' in line and '#' not in line and 'Read' not in line and line_num not in failed_lines:
                valid_line = True

        line_split = line.split(',')
        new_frame = int(line_split[0]) - 1
        line_modified = f"{' ' * (4 - len(str(new_frame)))}{new_frame},{','.join(line_split[1:]).rstrip(',')}\n"
        print_and_log(f"Replacing line {line_num + 1}: {line} to {line_modified.lstrip(' ')}", end='')

        celeste_tas[line_num] = line_modified
        with open(os.path.join(celeste_path, 'Celeste.tas'), 'w') as celeste_tas_file:
            celeste_tas_file.write(''.join(celeste_tas))

        run_tas()
        save_data = get_current_session(os.path.join(celeste_path, 'saves', 'debug.celeste'))
        new_level = save_data['level']
        new_time = int(save_data['time'])

        if new_level != target_level or new_time >= target_time:
            print_and_log(f"Didn't save time ({new_level}, {new_time})")
            failed_lines.append(line_num)

            celeste_tas[line_num] = original_line
            with open(os.path.join(celeste_path, 'Celeste.tas'), 'w') as celeste_tas_file:
                celeste_tas_file.write(''.join(celeste_tas))
        else:
            print_and_log(f"WORKED! {new_time} < {target_time} (original was {og_target_time})")
            failed_lines = []


def get_current_session(save_path):
    with open(save_path, 'r') as save_file:
        save_file_read = save_file.readlines()

    for line in save_file_read:
        if '<CurrentSession ' in line:
            soup = BeautifulSoup(line, 'lxml')
            currentsession = soup.find('currentsession')
            return {'time': currentsession.get('time'), 'level': currentsession.get('level')}


def run_tas():
    keyboard.press('`')
    time.sleep(0.1)
    keyboard.release('`')
    keyboard.press('up')
    time.sleep(0.1)
    keyboard.release('up')
    keyboard.press('enter')
    time.sleep(0.1)
    keyboard.release('enter')
    time.sleep(0.5)
    keyboard.press('`')
    time.sleep(0.1)
    keyboard.release('`')
    keyboard.press('p')
    time.sleep(0.1)
    keyboard.release('p')
    time.sleep(5)


def print_and_log(text, *args, **kwargs):
    print(text, *args, **kwargs)

    with open('output_log.txt', 'a') as output_log:
        output_log.write(text)


if __name__ == '__main__':
    main()
