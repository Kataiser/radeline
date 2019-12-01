import json
import os
import random
import time

import keyboard
from bs4 import BeautifulSoup


def main():
    failed_lines = []  # don't retry lines that are known to not work

    initial_delay = settings()['initial_delay_time_seconds']
    print_and_log(f"Starting in {initial_delay} seconds, switch to the Celeste window!")
    time.sleep(initial_delay)

    print_and_log("Getting reference data")
    run_tas()

    # assumes that Celeste.tas is currently functional and has a breakpoint at the end
    save_data = get_current_session(os.path.join(settings()['celeste_path'], 'saves', 'debug.celeste'))
    target_time = og_target_time = int(save_data['time'])
    target_level = save_data['level']
    print_and_log(f"Target time is {target_time} in level {target_level}")

    while True:
        with open(os.path.join(settings()['celeste_path'], 'Celeste.tas'), 'r') as celeste_tas_file_read:
            celeste_tas = celeste_tas_file_read.readlines()

        # find a valid line of input
        valid_line = False
        while not valid_line:
            line_num = random.randint(7, len(celeste_tas) - 1)  # the 7 is to ignore the chapter restart inputs
            original_line = celeste_tas[line_num]
            line = original_line.lstrip(' ').rstrip('\n')

            if ',' in line and '#' not in line and 'Read' not in line and line_num not in failed_lines:
                valid_line = True

        # split the line apart, subtract 1 from the frame number, and rebuild it
        line_split = line.split(',')
        new_frame = int(line_split[0]) - 1
        line_modified = f"{' ' * (4 - len(str(new_frame)))}{new_frame},{','.join(line_split[1:]).rstrip(',')}\n"
        print_and_log(f"Replacing line {line_num + 1}: {line} to {line_modified.lstrip(' ')}", end='')

        # save Celeste.tas with the changed line
        celeste_tas[line_num] = line_modified
        with open(os.path.join(settings()['celeste_path'], 'Celeste.tas'), 'w') as celeste_tas_file:
            celeste_tas_file.write(''.join(celeste_tas))

        # see if it worked
        run_tas()
        save_data = get_current_session(os.path.join(settings()['celeste_path'], 'saves', 'debug.celeste'))
        new_level = save_data['level']
        new_time = int(save_data['time'])

        if new_level != target_level or new_time >= target_time:  # don't count ties, rare as they are
            print_and_log(f"Didn't save time ({new_level}, {new_time})")  # same message regardless of failure reason
            failed_lines.append(line_num)

            # revert and save
            celeste_tas[line_num] = original_line
            with open(os.path.join(settings()['celeste_path'], 'Celeste.tas'), 'w') as celeste_tas_file:
                celeste_tas_file.write(''.join(celeste_tas))
        else:
            print_and_log(f"WORKED! {new_time} < {target_time} (original was {og_target_time})")
            target_time = new_time
            failed_lines = []


# read chapter time and current level (room) from debug.celeste
def get_current_session(save_path: str) -> dict:
    with open(save_path, 'r') as save_file:
        save_file_read = save_file.readlines()

    for line in save_file_read:
        if '<CurrentSession ' in line:
            soup = BeautifulSoup(line, 'lxml')  # probably overkill
            currentsession = soup.find('currentsession')
            return {'time': currentsession.get('time'), 'level': currentsession.get('level')}


# simulate keypresses to run the last debug command, run the TAS, and wait a bit
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
    time.sleep(settings()['worst_case_time'])


def print_and_log(text: str, *args, **kwargs):
    print(text, *args, **kwargs)

    with open('output_log.txt', 'a') as output_log:
        output_log.write(text)


def settings() -> dict:
    with open('settings.json.txt', 'r') as settings_file:
        return json.load(settings_file)


if __name__ == '__main__':
    main()
