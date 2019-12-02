import functools
import json
import os
import random
import time

import keyboard
from bs4 import BeautifulSoup


def main():
    failed_lines = []  # don't retry lines that are known to not work
    improved_lines = 0
    line_finding_timeout = settings()['line_finding_timeout']
    pause_key = settings()['pause_key']

    initial_delay = settings()['initial_delay_time']
    print_and_log(f"\n\nStarting in {initial_delay} seconds, switch to the Celeste window!")
    time.sleep(initial_delay)

    print_and_log("Getting reference data")
    run_tas(pauseable=False)

    # assumes that Celeste.tas is currently functional and has a breakpoint at the end
    save_data = get_current_session(os.path.join(settings()['celeste_path'], 'saves', 'debug.celeste'))
    target_time = og_target_time = int(save_data['time'])
    target_level = save_data['level']
    print_and_log(f"Target time is {target_time} in level {target_level}")

    with open(os.path.join(settings()['celeste_path'], 'Celeste.tas'), 'r') as celeste_tas_file_read:
        celeste_tas = celeste_tas_file_read.readlines()
    print_and_log(f"Beginning optimization of {len(celeste_tas)} lines in Celeste.tas. Press {pause_key} to pause, and make sure to keep the Celeste window focused.\n")

    while True:
        with open(os.path.join(settings()['celeste_path'], 'Celeste.tas'), 'r') as celeste_tas_file_read:
            celeste_tas = celeste_tas_file_read.readlines()

        input_file_trims = settings()['input_file_trims']
        lines_tried = 0
        search_start_time = time.perf_counter()

        # find a valid line of input
        valid_line = False
        while not valid_line:
            line_num = random.randrange(input_file_trims[0], len(celeste_tas) + input_file_trims[1])  # the 7 is to ignore the chapter restart inputs
            original_line = celeste_tas[line_num]
            line = original_line.lstrip(' ').rstrip('\n')
            lines_tried += 1

            if ',' in line and '#' not in line and 'Read' not in line and line_num not in failed_lines:
                valid_line = True
            else:
                # once we've run out of valid lines in the file
                if time.perf_counter() - search_start_time >= line_finding_timeout:
                    print_and_log(f"Valid input finding took {line_finding_timeout} seconds, exiting "
                                  f"({len(failed_lines)} scanned lines, {len(celeste_tas)} lines in Celeste.tas)")
                    raise SystemExit

        # split the line apart, subtract 1 from the frame number, and rebuild it
        line_split = line.split(',')
        new_frame = int(line_split[0]) - 1
        if 'F,' in line and settings()['tweak_feathers_angles'] and random.choice((True, False)):
            # 50/50 chance to tweak a feather angle instead
            tweaked_angle = int(line_split[-1]) + random.choice((-2, -1, 1, 2))
            line_modified = f"{' ' * (4 - len(str(line_split[0])))}{','.join(line_split[:-1])},{tweaked_angle}\n"
        else:
            line_modified = f"{' ' * (4 - len(str(new_frame)))}{new_frame},{','.join(line_split[1:]).rstrip(',')}\n"

        print_and_log(f"Replacing line {line_num + 1}/{len(celeste_tas)} (try {lines_tried}): {line} to {line_modified.lstrip(' ')[:-1]}")

        # save Celeste.tas with the changed line
        celeste_tas[line_num] = line_modified
        with open(os.path.join(settings()['celeste_path'], 'Celeste.tas'), 'w') as celeste_tas_file:
            celeste_tas_file.write(''.join(celeste_tas))

        # see if it worked
        paused = run_tas()
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
            improved_lines += 1
            print_and_log(f"IMPROVEMENT #{improved_lines} FOUND! {new_time} < {target_time} (original was {og_target_time})")
            target_time = new_time
            failed_lines = []

        if paused:
            print_and_log("Now paused. Press enter in this window to resume.")
            input()
            print_and_log(f"Resuming in {initial_delay} seconds, switch to the Celeste window")
            time.sleep(initial_delay)


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
def run_tas(pauseable=True):
    pause_key_code = keyboard.key_to_scan_codes(settings()['pause_key'])[0]
    has_paused = False

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
    start_time = time.perf_counter()
    time.sleep(0.5)

    while True:
        time.sleep(0.02)
        time_is_up = time.perf_counter() - start_time >= settings()['worst_case_time']

        if pauseable and not has_paused and keyboard.is_pressed(pause_key_code):
            has_paused = True
            print_and_log("Pause key pressed")

        if time_is_up:
            if pauseable:
                return has_paused
            else:
                break


def print_and_log(text: str):
    print(text)

    with open('output_log.txt', 'a') as output_log:
        output_log.write(f'{text}\n')


@functools.lru_cache(maxsize=1)
def settings() -> dict:
    with open('settings.json.txt', 'r') as settings_file:
        return json.load(settings_file)


if __name__ == '__main__':
    main()
