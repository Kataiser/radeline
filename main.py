# cython: language_level=3

import copy
import functools
import os
import platform
import random
import subprocess
import sys
import time
import traceback
from typing import Any, Dict, List, Sized, TextIO, Tuple, Union

import keyboard
import psutil
import requests
import win32gui
import yaml
from bs4 import BeautifulSoup


class Radeline:
    def __init__(self):
        if sys.version_info.major + (sys.version_info.minor / 10) < 3.6:  # probably not how you're supposed to do this
            print("Python >= 3.6 is required, exiting")

        sys.stdout = Logger()
        validate_settings()
        self.pids: Dict[str, Union[int, None]] = get_pids(init=True)
        self.improved_lines: List[int] = []
        self.improved_lines_formatted: str = ''
        self.frames_saved_total: int = 0
        self.initial_delay: Union[int, float] = settings()['initial_delay_time']
        self.target_data: dict = {}
        self.target_time: int = 0
        self.og_target_time: int = 0
        self.paused: bool = False
        self.pause_key_code: int = keyboard.key_to_scan_codes(settings()['pause_key'])[0]

    def run(self):
        pause_key: str = settings()['pause_key']
        input_file_trims: List[int] = settings()['input_file_trims']

        celeste_tas: List[str] = access_celeste_tas()
        celeste_tas_len: int = len(celeste_tas)  # keep the original length in case auto trim changes it
        if settings()['ensure_breakpoint_end'] and celeste_tas[-1] != '***':
            print("Celeste.tas doesn't end with a breakpoint (***), exiting")
            raise SystemExit

        print(f"Starting in {self.initial_delay} seconds, switch to the Celeste window!")
        time.sleep(self.initial_delay)

        # assumes that Celeste.tas is currently functional
        self.keep_game_focused()
        print("Getting reference data")
        self.run_tas(pauseable=False)

        self.target_data = parse_save_file()
        self.target_time = self.og_target_time = self.target_data['time']
        del self.target_data['time']

        if self.target_time == '0:00.000':
            print("Target time is 0:00.000, exiting (follow the instructions in the readme)")
            raise SystemExit

        print(f"Target time is {format_time(self.target_time)} with data {self.target_data}")

        # build a list of line numbers that are valid inputs
        if settings()['auto_trim']:
            celeste_tas_joined: str = ''.join(celeste_tas)

            if '#Start' in celeste_tas_joined:
                celeste_tas = '\n\n'.join(celeste_tas_joined.split('\n\n')[:-1]).split('\n')  # good code, gamers
                start_line_index: int = celeste_tas.index('#Start')
            else:
                print("Couldn't find \"#Start\" in Celeste.tas, using input_file_trims instead of auto trimming")
                start_line_index = 0
        else:
            start_line_index = 0

        valid_line_nums: List[int] = []

        for possible_line in enumerate(celeste_tas):
            if input_file_trims[0] < possible_line[0] < (len(celeste_tas) - input_file_trims[1]) or settings()['auto_trim']:
                line = possible_line[1]

                if '#' not in line and 'Read' not in line and ',' in line and not line.lstrip().startswith('0,') and (settings()['auto_trim'] and possible_line[0] > start_line_index):
                    valid_line_nums.append(possible_line[0])

        if settings()['auto_trim']:
            print(f"Auto trimmed Celeste.tas to lines {valid_line_nums[0]}-{valid_line_nums[-1] + 2}")
        else:
            print(f"Trimmed Celeste.tas to lines {input_file_trims[0] + 1}-{celeste_tas_len - input_file_trims[1]}")

        valid_line_nums = order_line_list(valid_line_nums)

        # perform the main operation
        print(f"Beginning optimization of Celeste.tas ({celeste_tas_len} lines, {len(valid_line_nums)} inputs)\n"
              f"Press {pause_key} to pause, and make sure to keep the Celeste window focused\n")
        time.sleep(settings()['loading_time_compensation'])
        self.reduce_lines(valid_line_nums)

        # do extra attempts for modified lines and a few neighbors
        if settings()['extra_attempts'] and self.improved_lines:
            extra_lines: List[int] = []
            window: int = settings()['extra_attempts_window_size']

            for line_num in self.improved_lines:
                for extra_line in range(line_num - window + 1, line_num + window):
                    if extra_line in valid_line_nums and extra_line not in extra_lines:
                        extra_lines.append(extra_line)

            extra_lines = order_line_list(extra_lines)

            print(f"\nFinished base processing, trying {len(extra_lines)} extra optimization{pluralize(extra_lines)}\n")
            self.reduce_lines(extra_lines)

        self.improved_lines_formatted = str(sorted([line + 1 for line in self.improved_lines]))[1:-1]
        print(f"\nFinished with {len(self.improved_lines)} optimization{pluralize(self.improved_lines)} found "
              f"({format_time(self.og_target_time)} -> {format_time(self.target_time)}, -{self.frames_saved_total}f)")

        if self.improved_lines_formatted:
            print(f"Line{pluralize(self.improved_lines)} changed: {self.improved_lines_formatted}")

        if settings()['exit_game_when_done']:
            psutil.Process(self.pids['celeste']).kill()

            try:
                psutil.Process(self.pids['studio']).kill()
                print("Closed Celeste and Studio")
            except psutil.NoSuchProcess:
                print("Closed Celeste")

        if settings()['open_celeste_tas_when_done'] and platform.system() == 'Windows':
            print("Opening Celeste.tas")
            os.startfile(os.path.join(settings()['celeste_path'], 'Celeste.tas'))

    # subtract 1 from a line and test if that helped, reverting if it didn't
    def reduce_line(self, line_num: int):
        # load this each time because it may have changed
        celeste_tas: List[str] = access_celeste_tas()

        # split the line apart, subtract 1 from the frame number, and rebuild it
        original_line: str = celeste_tas[line_num]
        line_clean: str = original_line.lstrip(' ').rstrip('\n')
        line_split: List[str] = line_clean.split(',')
        new_frame: int = int(line_split[0]) - 1
        line_modified: str = f"{' ' * (4 - len(str(new_frame)))}{new_frame},{','.join(line_split[1:]).rstrip(',')}\n"

        print(f"Line {line_num + 1}/{len(celeste_tas)}: {line_clean} to {line_modified.lstrip(' ')[:-1]}")

        # save Celeste.tas with the changed line
        celeste_tas[line_num] = line_modified
        access_celeste_tas(write=celeste_tas)

        # run with the changed line
        self.run_tas(pauseable=True)
        new_data: dict = parse_save_file()
        new_time: int = new_data['time']
        del new_data['time']

        if new_time == 0:
            frames_saved: Union[int, None] = None
            frames_lost: Union[int, None] = None
        else:
            frames_saved = compare_timecode_frames(self.target_time, new_time)
            frames_lost = compare_timecode_frames(new_time, self.target_time)

        # output message if it almost worked
        if new_time >= self.target_time and new_data == self.target_data:
            print(f"Resynced but didn't save time: ({format_time(new_time)} >= {format_time(self.target_time)}, +{frames_lost}f)")
        if new_data['room'] == self.target_data['room']:
            time.sleep(settings()['loading_time_compensation'])

            if new_data != self.target_data:
                display_data: dict = copy.deepcopy(new_data)
                del display_data['room']
                print(f"Resynced but didn't get correct collectibles: {display_data}")

        # see if it worked (don't count ties)
        if new_time < self.target_time and new_data == self.target_data:
            self.improved_lines.append(line_num)
            self.frames_saved_total = compare_timecode_frames(self.og_target_time, new_time)
            print(f"OPTIMIZATION #{len(self.improved_lines)} FOUND! {format_time(new_time)} < {format_time(self.target_time)}, -{frames_saved}f "
                  f"(original was {format_time(self.og_target_time)}, -{self.frames_saved_total}f)")
            self.target_time = new_time
        else:
            # revert and save
            celeste_tas[line_num] = original_line
            access_celeste_tas(write=celeste_tas)

        if self.paused:
            improved_lines_num = len(self.improved_lines)
            print(f"Now paused, press enter in this window to resume "
                  f"(currently at {improved_lines_num} optimization{pluralize(improved_lines_num)}, -{self.frames_saved_total}f)")
            input()
            print(f"Resuming in {self.initial_delay} seconds, switch to the Celeste window\n")
            time.sleep(self.initial_delay)

            settings.cache_clear()  # reload settings file
            validate_settings()
            self.pids = get_pids(silent=True)

    # simulate keypresses to run the last debug command, run the TAS, and wait a bit
    def run_tas(self, pauseable: bool):
        if not psutil.pid_exists(self.pids['celeste']):
            print("\nCeleste has been closed, pausing")
            self.paused = True

        consecutive: int = settings()['session_consecutive']
        interval: float = float(settings()['session_interval'])
        timeout: float = float(settings()['session_timeout'])
        pos_history: List[Tuple[str, str]] = []
        tas_has_finished: bool = False

        self.paused = False

        if not settings()['console_load_mode']:
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
            time.sleep(0.5)
            keyboard.release('`')

        keyboard.press(12)  # - (minus/hyphen)
        time.sleep(0.1)
        keyboard.release(12)
        time.sleep(0.5)
        start_time: float = time.perf_counter()
        last_request_time: float = start_time

        while True:
            if pauseable and not self.paused and keyboard.is_pressed(self.pause_key_code):
                self.paused = True
                print("\nPause key pressed")  # technically not paused yet

            if time.perf_counter() - last_request_time >= interval:
                # just ask the game when the TAS has finished lol
                session_data: List[str] = requests.get('http://localhost:32270/session').text.split('\r\n')
                pos_history.append((session_data[4], session_data[5]))  # x and y
                tas_has_finished = len(pos_history) > consecutive * 2 and len(set(pos_history[-consecutive:])) == 1
                last_request_time = time.perf_counter()

            if tas_has_finished or time.perf_counter() - start_time > timeout:  # just in case the server based detection fails somehow
                break

    # perform reduce_line() for a list of line numbers
    def reduce_lines(self, lines: List[int]):
        for line_enum in enumerate(lines):
            self.keep_game_focused()  # do this before everything to keep both Celeste.tas and the output clean

            progress: str = format((line_enum[0] / (len(lines) - 1)) * 100, '.1f')
            print(f"({progress}%) ", end='')

            self.reduce_line(line_enum[1])

    # if the game isn't the focused window, wait until it is or until a timeout
    def keep_game_focused(self):
        focused_window: str = win32gui.GetWindowText(win32gui.GetForegroundWindow())

        if 'Celeste' not in focused_window:
            print("\nCeleste is not in focus, waiting until it is...")

            while focused_window != 'Celeste':
                focused_window: str = win32gui.GetWindowText(win32gui.GetForegroundWindow())
                time.sleep(1)

            print(f"Celeste has been focused, resuming in {self.initial_delay} seconds...\n")
            time.sleep(self.initial_delay)


# read chapter time and current level (room) from debug.celeste
def parse_save_file() -> dict:
    with open(os.path.join(settings()['celeste_path'], 'saves', 'debug.celeste'), 'r') as save_file:
        save_file_read = save_file.read()

    parsed: dict = {}
    soup: BeautifulSoup = BeautifulSoup(save_file_read, 'lxml')

    currentsession = soup.find('currentsession_safe')
    if currentsession is None:
        currentsession = soup.find('currentsession')
    if currentsession is None:
        print("Couldn't find a CurrentSession tag in debug.celeste, guess the game broke? IDK, exiting anyway")

    parsed['time'] = int(currentsession.get('time'))
    parsed['room'] = currentsession.get('level')
    parsed['cassette'] = currentsession.get('cassette')
    parsed['heart'] = currentsession.get('heartgem')
    parsed['keys'] = len(soup.find_all('keys')[0].find_all('entityid'))

    totalstrawberries = soup.find('totalstrawberries')
    parsed['berries'] = int(totalstrawberries.text)

    return parsed


# convert the weird timecodes Celeste uses into a readable format
@functools.lru_cache(maxsize=None)
def format_time(timecode: int) -> str:
    timecode_str: str = str(timecode)

    try:
        minutes: int = int(int(timecode_str[:-7]) / 60)
        seconds: int = int(int(timecode_str[:-7]) % 60)
        ms: int = int(timecode_str[-7:-4])

        return f"{minutes}:{str(seconds).rjust(2, '0')}.{str(ms).rjust(3, '0')}"
    except ValueError:
        return '0:00.000'


# find the difference between two timecodes, in frames (timecode_1 - timecode_2, assumes < 1 second diff)
@functools.lru_cache(maxsize=None)
def compare_timecode_frames(timecode_1: int, timecode_2: int) -> int:
    if timecode_1 == timecode_2:
        return 0
    else:
        seconds_1: int = int(int(str(timecode_1)[:-7]) % 60)
        seconds_2: int = int(int(str(timecode_2)[:-7]) % 60)

        ms_1: int = int(str(timecode_1)[-7:-4])
        ms_2: int = int(str(timecode_2)[-7:-4])

        if seconds_1 == seconds_2:
            return round((ms_1 - ms_2) / 17)
        else:
            return round(ms_1 / 17) + round((1000 - ms_2) / 17)


def access_celeste_tas(write: List[str] = None):
    with open(os.path.join(settings()['celeste_path'], 'Celeste.tas'), 'r+') as celeste_tas_file:
        if write:
            celeste_tas_file.write(''.join(write))
        else:
            return celeste_tas_file.readlines()


# get the process IDs for Celeste and Studio
def get_pids(silent: bool = False, init: bool = False) -> Dict[str, Union[int, None]]:
    found_pids: Dict[str, Union[int, None]] = {'celeste': None, 'studio': None}

    # https://docs.microsoft.com/en-us/windows-server/administration/windows-commands/tasklist
    try:
        processes: List[str] = str(subprocess.check_output('tasklist /fi "STATUS eq running"')).split(r'\r\n')
    except subprocess.CalledProcessError:
        processes = []

    for process_line in processes:
        process: List[str] = process_line.split()

        if process[0] == 'Celeste.exe':
            found_pids['celeste'] = int(process[1])
        elif 'studio' in process[0].lower() and 'celeste' in process[0].lower():
            found_pids['studio'] = int(process[1])

    if not found_pids['celeste']:
        if not init:
            print("")

        print("Celeste isn't running, exiting")
        raise SystemExit

    if not silent:
        if found_pids['studio']:
            print("Found Celeste.exe and Celeste.Studio.exe")
        else:
            print("Found Celeste.exe")

    return found_pids


# or most likely, disorder
def order_line_list(lines: List[int]) -> List[int]:
    order: str = settings()['order']

    if order == 'forward':
        lines.sort()
    elif order == 'reverse':
        lines.sort()
        lines.reverse()
    elif order == 'random':
        random.shuffle(lines)

    return lines


# just to make sure the user hasn't broken anything
def validate_settings():
    try:
        settings()
    except yaml.YAMLError as error:
        error_tabbed: str = str(error).replace('\n', '\n    ')
        print(f"Couldn't parse settings:\n    {error_tabbed}")
        raise SystemExit

    celeste_path: str = str(settings()['celeste_path'])
    bool_settings = ('exit_game_when_done', 'clear_output_log_on_startup', 'open_celeste_tas_when_done', 'extra_attempts', 'keep_celeste_focused',
                     'console_load_mode', 'ensure_breakpoint_end', 'auto_trim')
    int_settings = ('extra_attempts_window_size', 'session_consecutive')
    num_settings = ('initial_delay_time', 'loading_time_compensation', 'focus_wait_timeout', 'session_timeout', 'session_interval')  # int or float

    # makes sure that each setting is what type it needs to be, and some other checks as well
    if not os.path.isdir(celeste_path):
        invalid_setting(f"\"{celeste_path}\" doesn't exist")
    if 'Celeste.exe' not in os.listdir(celeste_path):
        invalid_setting(f"\"{celeste_path}\" is not a valid Celeste installation")
    for bool_setting in bool_settings:
        if not isinstance(settings()[bool_setting], bool):
            invalid_setting(f"\"{bool_setting}\" is not either true or false")
    for int_setting in int_settings:
        if not isinstance(settings()[int_setting], int):
            invalid_setting(f"\"{int_setting}\" is not an integer")
    for num_setting in num_settings:
        if not isinstance(settings()[num_setting], int) and not isinstance(settings()[num_setting], float):
            invalid_setting(f"\"{num_setting}\" is not a number")
    if settings()['order'] not in ('forward', 'reverse', 'random'):
        invalid_setting("\"order\" is not forward, reverse, or random")
    if len(settings()['input_file_trims']) != 2:
        invalid_setting("\"input_file_trims\" is not two items long")
    for trim in enumerate(settings()['input_file_trims']):
        if not isinstance(trim[1], int):
            invalid_setting(f"item {trim[0] + 1} is not an integer")
    if not isinstance(settings()['pause_key'], str):
        invalid_setting("\"pause_key\" is not text")
    try:
        keyboard.key_to_scan_codes(settings()['pause_key'])
    except ValueError:
        invalid_setting("\"pause_key\" is not a valid key")


def invalid_setting(error_message: str):
    print(f"Settings loading error: {error_message}")
    raise SystemExit


def pluralize(count: Union[int, Sized]) -> str:
    if isinstance(count, int):
        return 's' if count != 1 else ''
    else:
        return 's' if len(count) != 1 else ''


@functools.lru_cache(maxsize=1)
def settings() -> Dict[str, Any]:
    with open('settings.yaml', 'r') as settings_file:
        return yaml.safe_load(settings_file)


# log all prints to a file
class Logger(object):
    def __init__(self):
        if settings()['clear_output_log_on_startup'] and os.path.isfile('output_log.txt'):
            os.remove('output_log.txt')

        self.terminal: TextIO = sys.stdout
        self.log: TextIO = open('output_log.txt', 'a')

    def write(self, message):
        self.terminal.write(message)
        self.log.write(message)
        self.log.flush()

    def flush(self):
        pass


def main():
    try:
        radeline = Radeline()
        radeline.run()
    except Exception:
        print(traceback.format_exc())


if __name__ == '__main__':
    main()
