import copy
import functools
import json
import os
import random
import time

import keyboard
from bs4 import BeautifulSoup


def main():
    improved_lines = 0
    pause_key = settings()['pause_key']
    input_file_trims = settings()['input_file_trims']

    initial_delay = settings()['initial_delay_time']
    print_and_log(f"\n\nStarting in {initial_delay} seconds, switch to the Celeste window!")
    time.sleep(initial_delay)

    print_and_log("Getting reference data")
    run_tas(pauseable=False)

    # assumes that Celeste.tas is currently functional and has a breakpoint at the end
    target_data = parse_save_file(os.path.join(settings()['celeste_path'], 'saves', 'debug.celeste'))
    target_time = og_target_time = target_data['time']
    del target_data['time']
    print_and_log(f"Target time is {format_time(target_time)} with data {target_data}")

    with open(os.path.join(settings()['celeste_path'], 'Celeste.tas'), 'r') as celeste_tas_file_read:
        celeste_tas = celeste_tas_file_read.readlines()

    # build a list of line numbers that are valid inputs
    valid_line_nums = []
    for possible_line in enumerate(celeste_tas):
        if input_file_trims[0] < possible_line[0] < (len(celeste_tas) + input_file_trims[1]):
            if ',' in possible_line[1] and '#' not in possible_line[1] and 'Read' not in possible_line[1]:
                valid_line_nums.append(possible_line[0])

    if settings()['random_order']:
        random.shuffle(valid_line_nums)

    print_and_log(f"Beginning optimization of Celeste.tas ({len(celeste_tas)} lines, {len(valid_line_nums)} inputs). "
                  f"Press {pause_key} to pause, and make sure to keep the Celeste window focused.\n")

    for valid_line in enumerate(valid_line_nums):
        # load this each time because it may have changed
        with open(os.path.join(settings()['celeste_path'], 'Celeste.tas'), 'r') as celeste_tas_file_read:
            celeste_tas = celeste_tas_file_read.readlines()

        # split the line apart, subtract 1 from the frame number, and rebuild it
        line_num = valid_line[1]
        original_line = celeste_tas[line_num]
        line = original_line.lstrip(' ').rstrip('\n')
        line_split = line.split(',')
        new_frame = int(line_split[0]) - 1
        line_modified = f"{' ' * (4 - len(str(new_frame)))}{new_frame},{','.join(line_split[1:]).rstrip(',')}\n"

        # output progress
        progress = format((valid_line[0] / len(valid_line_nums)) * 100, '.1f')
        print_and_log(f"({progress}%) Line {line_num + 1}/{len(celeste_tas)}: {line} to {line_modified.lstrip(' ')[:-1]}")

        # save Celeste.tas with the changed line
        celeste_tas[line_num] = line_modified
        with open(os.path.join(settings()['celeste_path'], 'Celeste.tas'), 'w') as celeste_tas_file:
            celeste_tas_file.write(''.join(celeste_tas))

        # run with the changed line
        paused = run_tas()
        new_data = parse_save_file(os.path.join(settings()['celeste_path'], 'saves', 'debug.celeste'))
        new_time = new_data['time']
        del new_data['time']

        # output message if it almost worked
        if new_time >= target_time and new_data == target_data:
            print_and_log(f"Resynced but didn't save time {format_time(new_time)} >= {format_time(target_time)}")
        if new_data['level'] == target_data['level'] and new_data != target_data:
            display_data = copy.deepcopy(new_data)
            del display_data['level']
            print_and_log(f"Resynced but didn't get correct collectibles {display_data}")

        # see if it worked (don't count ties, rare as they are)
        if new_time < target_time and new_data == target_data:
            improved_lines += 1
            print_and_log(f"IMPROVEMENT #{improved_lines} FOUND! {format_time(new_time)} < {format_time(target_time)} (original was {format_time(og_target_time)})")
            target_time = new_time
        else:
            # revert and save
            celeste_tas[line_num] = original_line
            with open(os.path.join(settings()['celeste_path'], 'Celeste.tas'), 'w') as celeste_tas_file:
                celeste_tas_file.write(''.join(celeste_tas))

        if paused:
            print_and_log("Now paused. Press enter in this window to resume.")
            input()
            print_and_log(f"Resuming in {initial_delay} seconds, switch to the Celeste window\n")
            time.sleep(initial_delay)
            settings.cache_clear()  # reload settings file
            
    print_and_log(f"\nFinished with {improved_lines} optimization{'s' if improved_lines != 1 else ''} found ({format_time(og_target_time)} -> {format_time(target_time)})")

    if settings()['exit_game_when_done']:
        print_and_log("Closing Celeste")
        # super ugly
        keyboard.press('`')
        time.sleep(0.1)
        keyboard.release('`')
        keyboard.press('e')
        time.sleep(0.1)
        keyboard.release('e')
        keyboard.press('tab')
        time.sleep(0.1)
        keyboard.release('tab')
        time.sleep(0.1)
        keyboard.press('tab')
        time.sleep(0.1)
        keyboard.release('tab')
        keyboard.press('enter')
        time.sleep(0.1)
        keyboard.release('enter')

    raise SystemExit


# read chapter time and current level (room) from debug.celeste
def parse_save_file(save_path: str) -> dict:
    with open(save_path, 'r') as save_file:
        save_file_read = save_file.readlines()

    parsed = {}

    for line in save_file_read:
        if '<CurrentSession ' in line:
            soup = BeautifulSoup(line, 'lxml')  # probably overkill
            currentsession = soup.find('currentsession')
            parsed['time'] = int(currentsession.get('time'))
            parsed['level'] = currentsession.get('level')
            parsed['cassette'] = currentsession.get('cassette')
            parsed['heartgem'] = currentsession.get('heartgem')
        elif '<TotalStrawberries>' in line:
            soup = BeautifulSoup(line, 'lxml')  # definitely overkill
            totalstrawberries = soup.find('totalstrawberries')
            parsed['total_berries'] = int(totalstrawberries.text)

    return parsed


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
            print_and_log("\nPause key pressed")  # technically not paused yet

        if time_is_up:
            if pauseable:
                return has_paused
            else:
                break


def format_time(timecode: int) -> str:
    timecode_str = str(timecode)

    try:
        minutes = int(int(timecode_str[:-7]) / 60)
        seconds = int(int(timecode_str[:-7]) % 60)
        ms = int(timecode_str[-7:-4])

        return f"{minutes}:{str(seconds).rjust(2, '0')}.{str(ms).rjust(3, '0')}"
    except ValueError:
        return '0:0.000'


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
