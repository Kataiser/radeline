import _thread
import copy
import functools
import os
import platform
import random
import re
import shutil
import subprocess
import sys
import threading
import time
import traceback
from typing import Any, Callable, Dict, List, Optional, Sized, TextIO, Union

import keyboard
import psutil
import requests
import yaml
from bs4 import BeautifulSoup

import update_check


class Radeline:
    def __init__(self):
        if sys.version_info.major < 3 or sys.version_info.minor < 6:
            print("Python >= 3.6 is required, exiting")

        sys.stdout = Logger()
        validate_settings()
        update_check.is_latest_commit()
        self.pids: Dict[str, Optional[int]] = get_pids(init=True)
        self.celeste_path: Optional[str] = None
        self.debugrc_address: Optional[str] = None
        self.improved_lines: List[int] = []
        self.improved_lines_formatted: str = ''
        self.frames_saved_total: int = 0
        self.target_data: dict = {}
        self.target_time: int = 0
        self.og_target_time: int = 0
        self.paused: bool = False
        self.pause_key_code: int = keyboard.key_to_scan_codes(settings()['pause_key'])[0]

    def run(self):
        pause_key: str = settings()['pause_key']
        input_file_trims: List[int] = settings()['input_file_trims']

        celeste_tas: List[str] = access_tas_file()
        celeste_tas_len: int = len(celeste_tas)  # keep the original length in case auto trim changes it
        while settings()['ensure_breakpoint_end'] and not ends_with_breakpoint(celeste_tas):
            print("The TAS doesn't end with a breakpoint (***), pausing (press enter to retry)")
            input()
            celeste_tas: List[str] = access_tas_file()
            celeste_tas_len: int = len(celeste_tas)

        # build a list of line numbers that are valid inputs
        if settings()['auto_trim']:
            celeste_tas_joined: str = ''.join(celeste_tas)

            if '#Start' in celeste_tas_joined:
                celeste_tas = '\n\n'.join(celeste_tas_joined.split('\n\n')[:-1]).split('\n')  # good code, gamers
                start_line_index: int = celeste_tas.index('#Start')
            else:
                print("Couldn't find \"#Start\" in the TAS, using input_file_trims instead of auto trimming")
                start_line_index = 0
        else:
            start_line_index = 0

        valid_line_nums: List[int] = []

        for possible_line in enumerate(celeste_tas):
            if input_file_trims[0] <= possible_line[0] < (len(celeste_tas) - input_file_trims[1]) or settings()['auto_trim']:
                if possible_line[0] > start_line_index and possible_line[1].lstrip().partition(',')[0].isdigit():
                    valid_line_nums.append(possible_line[0])

        if settings()['auto_trim']:
            print(f"Auto trimmed the TAS to lines {valid_line_nums[0]}-{valid_line_nums[-1] + 2}")
        else:
            print(f"Trimmed the TAS to lines {input_file_trims[0] + 1}-{celeste_tas_len - input_file_trims[1]}")

        valid_line_nums = order_line_list(valid_line_nums)
        self.celeste_path = psutil.Process(self.pids['celeste']).cwd()
        self.debugrc_address = get_debugrc_address(self.celeste_path)
        print("Getting reference data")
        # assumes that the TAS is currently functional
        self.run_tas(pauseable=False)
        self.target_data = self.parse_save_file(init=True)

        if not self.target_data:
            print("Reference data is necessary, exiting")
            raise SystemExit
        elif format_time(self.target_data['time']) == '0:00.000':
            print("Target time is 0:00.000, exiting (follow the instructions in the readme)")
            raise SystemExit

        # perform the main operation
        self.target_time = self.og_target_time = self.target_data['time']
        del self.target_data['time']
        print(f"Target time is {format_time(self.target_time)} with data {self.target_data}")
        backup_tas_file(self.target_time)
        print(f"Beginning optimization ({celeste_tas_len} lines, {len(valid_line_nums)} inputs)\n"
              f"Press {pause_key} to pause\n")
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
            self.close_running_programs()

        if settings()['open_tas_when_done'] and platform.system() == 'Windows':
            print("Opening the TAS")
            os.startfile(settings()['tas_path'])

    # subtract 1 from a line and test if that helped, reverting if it didn't
    def reduce_line(self, line_num: int, progess_percent: float, feather_adjust: int = 0) -> bool:
        print(f"({format(progess_percent, '.1f')}%){'*' if feather_adjust != 0 else ''} ", end='')

        # load this each time because it may have changed
        celeste_tas: List[str] = access_tas_file()

        # split the line apart, subtract 1 from the frame number, and rebuild it
        original_line: str = celeste_tas[line_num]
        line_clean: str = original_line.lstrip(' ').rstrip('\n')
        line_split: List[str] = line_clean.split(',') if ',' in line_clean else [line_clean]
        new_frame: int = int(line_split[0]) - 1

        if 'F,' in line_clean and feather_adjust != 0:
            line_split[-1] = '360' if line_split[-1] == '' else line_split[-1]
            tweaked_angle: int = round(float(line_split[-1])) + feather_adjust
            tweaked_angle = 360 + tweaked_angle if tweaked_angle <= 0 else tweaked_angle
            tweaked_angle = tweaked_angle - 360 if tweaked_angle > 360 else tweaked_angle
            line_modified: str = f"{' ' * (4 - len(str(new_frame)))}{new_frame},{','.join(line_split[1:-1])},{tweaked_angle}\n"
        else:
            line_modified = f"{' ' * (4 - len(str(new_frame)))}{new_frame}{',' if line_split[1:] else ''}{','.join(line_split[1:]).rstrip(',')}\n"

        print(f"Line {line_num + 1}/{len(celeste_tas)}: {line_clean} to {line_modified.lstrip(' ')[:-1]}")

        # save with the changed line
        celeste_tas[line_num] = line_modified
        access_tas_file(write=celeste_tas)

        # run with the changed line
        self.run_tas(pauseable=True)
        new_data: dict = self.parse_save_file()

        if new_data:
            new_time: int = new_data['time']
            del new_data['time']
        else:
            return False  # skip line in case of debug.celeste errors

        if new_time == 0:
            frames_saved: Optional[int] = None
            frames_lost: Optional[int] = None
        else:
            frames_saved = compare_timecode_frames(self.target_time, new_time)
            frames_lost = compare_timecode_frames(new_time, self.target_time)

        # output message if it almost worked
        if new_time > self.target_time and new_data == self.target_data:
            print(f"Resynced but lost time: ({format_time(new_time)} >= {format_time(self.target_time)}, +{frames_lost}f)")
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
            optimize_feathers: bool = False
            saved_time: bool = True
        else:
            # revert and save
            celeste_tas[line_num] = original_line
            access_tas_file(write=celeste_tas)
            optimize_feathers = settings()['optimize_feathers'] and 'F,' in line_clean and feather_adjust == 0
            saved_time = False

        if self.paused:
            improved_lines_num = len(self.improved_lines)
            print(f"Now paused, press enter in this window to resume "
                  f"(currently at {improved_lines_num} optimization{pluralize(improved_lines_num)}, -{self.frames_saved_total}f)")
            input()
            print(f"Resuming\n")

            settings.cache_clear()  # reload settings file
            validate_settings()
            self.pids = get_pids(silent=True)

        # works by reducing inputs by one again, but this time with slightly changed feather angles
        if optimize_feathers:
            feather_window: int = settings()['feather_degree_window_size']

            for offset in [i for i in range(-feather_window, feather_window + 1) if i != 0]:
                if self.reduce_line(line_num, progess_percent, feather_adjust=offset):
                    # if a feather change saved time, don't overwrite it
                    break

        return saved_time

    # simulate keypresses to run the last debug command, run the TAS, and wait a bit
    def run_tas(self, pauseable: bool):
        interval: float = float(settings()['session_interval'])
        short_timeout: float = float(settings()['session_short_timeout'])
        long_timeout: float = float(settings()['session_long_timeout'])
        alt_timeout_method: bool = settings()['session_alt_timeout_method']
        server_url_start: str = f'{self.debugrc_address}tas/sendhotkey?id=Restart'
        server_url_tasinfo: str = f'{self.debugrc_address}tas/info'
        tas_has_finished: bool = False
        self.paused = False

        if alt_timeout_method:
            @timeout(short_timeout)
            def request_force_timeout(url: str):
                return requests.get(url)

        # start the TAS via DebugRC
        requests.post(server_url_start, timeout=long_timeout)
        start_time: float = time.perf_counter()
        last_request_time: float = start_time

        while True:
            current_time: float = time.perf_counter()

            if pauseable and not self.paused and keyboard.is_pressed(self.pause_key_code) and not keyboard.is_pressed(42):  # 42 is shift
                self.paused = True
                print("\nPause key pressed")  # technically not paused yet

            if current_time - last_request_time >= interval and current_time - start_time > 2:
                try:
                    # just ask the game when the TAS has finished lol
                    if alt_timeout_method:
                        session_data: str = request_force_timeout(server_url_tasinfo).text
                    else:
                        session_data = requests.get(server_url_tasinfo, timeout=short_timeout).text
                except (requests.ConnectionError, requests.ReadTimeout):
                    # the game probably crashed
                    self.restart_game()
                    tas_has_finished = True
                else:
                    tas_has_finished = "Running: False" in session_data

                    if tas_has_finished:
                        time.sleep(settings()['session_wait'])

            if tas_has_finished or current_time - start_time > long_timeout:  # just in case the server based detection fails somehow
                break

    # perform reduce_line() for a list of line numbers
    def reduce_lines(self, lines: List[int]):
        for line_enum in enumerate(lines):
            progress: float = (line_enum[0] / (len(lines) - 1)) * 100
            self.reduce_line(line_enum[1], progress)

    # for if the game crashes mid-optimization
    def restart_game(self):
        time.sleep(settings()['restart_prewait'])

        if settings()['restart_crashed_game']:
            if not get_pids(silent=True, allow_exit=False)['celeste']:
                print("\nThe game seems to have crashed, trying to restart it and continue...")
                self.close_running_programs(include_notepads=True)
                og_cwd = os.getcwd()
                os.chdir(os.path.dirname(self.celeste_path))
                subprocess.Popen(f'{self.celeste_path}\\Celeste.exe', creationflags=0x00000010)  # the creationflag is for not waiting until the process exits
                time.sleep(settings()['restart_postwait'])
                os.chdir(og_cwd)
                self.pids = get_pids()
                print()
                self.run_tas(pauseable=True)

    # force close the processes of Celeste, Studio, and notepads (optional)
    def close_running_programs(self, include_notepads: bool = False):
        if self.pids['celeste']:
            try:
                psutil.Process(self.pids['celeste']).kill()
                print("Closed Celeste")
            except psutil.NoSuchProcess:
                pass

        if self.pids['studio']:
            try:
                psutil.Process(self.pids['studio']).kill()
                print("Closed Celeste Studio")
            except psutil.NoSuchProcess:
                pass

        if include_notepads and settings()['kill_notepads']:
            for proc in psutil.process_iter():
                try:
                    if 'notepad' in proc.name().lower() or 'wordpad' in proc.name().lower():
                        print(f"Closed {proc.name()}")
                        proc.kill()
                except (psutil.AccessDenied, psutil.NoSuchProcess):
                    pass

    # read chapter time and current level (room) from debug.celeste
    def parse_save_file(self, init: bool = False) -> dict:
        try:
            with open(os.path.join(self.celeste_path, 'saves', 'debug.celeste'), 'r') as save_file:
                save_file_read = save_file.read()
        except PermissionError:
            time.sleep(2)
            with open(os.path.join(self.celeste_path, 'saves', 'debug.celeste'), 'r') as save_file:
                save_file_read = save_file.read()
        except FileNotFoundError:
            print(f"Can't find debug.celeste{'' if init else ', skipping line'}")
            return {}

        parsed: dict = {}
        soup: BeautifulSoup = BeautifulSoup(save_file_read, 'lxml')

        currentsession = soup.find('currentsession_safe')
        if currentsession is None:
            currentsession = soup.find('currentsession')
        if currentsession is None:
            print(f"Couldn't find a CurrentSession tag in debug.celeste, guess the game broke? IDK{'' if init else ', skipping line anyway'}")
            return {}

        parsed['time'] = int(currentsession.get('time'))
        parsed['room'] = currentsession.get('level')
        parsed['cassette'] = currentsession.get('cassette')
        parsed['heart'] = currentsession.get('heartgem')
        parsed['keys'] = len(soup.find_all('keys')[0].find_all('entityid'))

        totalstrawberries = soup.find('totalstrawberries')
        parsed['berries'] = int(totalstrawberries.text)

        return parsed


# convert the weird timecodes Celeste uses into a readable format
@functools.cache
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
@functools.cache
def compare_timecode_frames(timecode_1: int, timecode_2: int) -> int:
    if timecode_1 == timecode_2:
        return 0
    else:
        if timecode_1 < 10000000 or timecode_2 < 10000000:
            # this happens rarely, idk how to handle it so just give up
            print(f"Unparseble timecode: {min(timecode_1, timecode_2)}", file=sys.stderr)
            return 0

        seconds_1: int = int(int(str(timecode_1)[:-7]) % 60)
        seconds_2: int = int(int(str(timecode_2)[:-7]) % 60)

        ms_1: int = int(str(timecode_1)[-7:-4])
        ms_2: int = int(str(timecode_2)[-7:-4])

        if seconds_1 == seconds_2:
            return round((ms_1 - ms_2) / 17)
        else:
            return round(ms_1 / 17) + round((1000 - ms_2) / 17)


# read or write to the chosen TAS file
def access_tas_file(write: List[str] = None) -> Optional[List[str]]:
    while True:
        try:
            path: str = settings()['tas_path']

            if not os.path.isfile(path):
                print(f"The TAS path you entered ({path}) doesn't seem to exist, exiting")

            with open(path, 'r+') as celeste_tas_file:
                if write:
                    celeste_tas_file.write(''.join(write))
                    return
                else:
                    tas_file_lines: List[str] = celeste_tas_file.readlines()

            if tas_file_lines:
                return tas_file_lines
            else:
                print(f"The TAS path you entered ({path}) seems to be empty, exiting")
        except PermissionError:
            time.sleep(0.5)


# backs up the current TAS file before ever trying to modify it, just in case it gets broken somehow
def backup_tas_file(file_time: int):
    if not os.path.isdir('Backups'):
        os.mkdir('Backups')
        time.sleep(0.2)

    path: str = settings()['tas_path']
    tas_filename: str = os.path.basename(os.path.splitext(path)[0])
    time_formatted: str = format_time(file_time).replace(':', '-')
    output_file = f'Backups\\{tas_filename}_{time_formatted}.tas'
    shutil.copy(path, output_file)
    print(f"Backed up to {output_file}")


# get the process IDs for Celeste and Studio
def get_pids(silent: bool = False, init: bool = False, allow_exit: bool = True) -> Dict[str, Optional[int]]:
    found_pids: Dict[str, Optional[int]] = {'celeste': None, 'studio': None}

    # https://docs.microsoft.com/en-us/windows-server/administration/windows-commands/tasklist
    try:
        processes: List[str] = str(subprocess.check_output('tasklist /fi "STATUS eq running"')).split(r'\r\n')
    except subprocess.CalledProcessError:
        processes = []

    for process_line in processes:
        if '.exe' not in process_line:
            continue

        process_name: str = process_line.split('.exe')[0]
        process_pid: int = int(process_line.split('.exe')[1].split()[0])

        if process_name == 'Celeste':
            found_pids['celeste'] = process_pid
        elif 'studio' in process_name.lower() and 'celeste' in process_name.lower():
            found_pids['studio'] = process_pid

    if allow_exit and None in found_pids.values():
        if not init:
            print("")

        if found_pids['celeste'] and not found_pids['studio']:
            print("Celeste Studio isn't running, exiting")
        else:
            print("Celeste isn't running, exiting")

        raise SystemExit

    if not silent:
        print("Found Celeste.exe and Celeste Studio.exe")

    return found_pids


# realistically this is more to check if the server started, cause why would the user change the port
def get_debugrc_address(celeste_path: str) -> str:
    with open(os.path.join(celeste_path, 'log.txt'), 'r', encoding='UTF8', errors='replace') as log_txt:
        log_txt_read: str = log_txt.read()

    debugrc_match = re.search(r'Started DebugRC thread, available via http://localhost:[0-9]+/', log_txt_read)

    if debugrc_match:
        debugrc_line = log_txt_read[debugrc_match.regs[0][0]:debugrc_match.regs[0][1]]  # there's gotta be a better way of doing this but I'm bad
        return debugrc_line.split()[-1]
    else:
        print("DebugRC server not running, exiting")
        raise SystemExit


# or most likely, disorder
def order_line_list(lines: List[int]) -> List[int]:
    order: str = settings()['order']

    if order == 'random':
        random.shuffle(lines)
    else:
        lines.sort(reverse=order == 'reverse')

    return lines


# properly accounts for non-input lines after the breakpoint
def ends_with_breakpoint(tas: List[str]) -> bool:
    last_line_is_breakpoint: bool = False

    for line in tas:
        if line in ('***', '***\n'):
            last_line_is_breakpoint = True
        else:
            line_stripped: str = line.lstrip()

            if line_stripped and line_stripped[0].isdigit():
                last_line_is_breakpoint = False

    return last_line_is_breakpoint


# decorator to kill a synchronous function after some time
def timeout(seconds: float):
    def outer(func: Callable):
        def inner(*args, **kwargs):
            timer: threading.Timer = threading.Timer(seconds, _thread.interrupt_main)
            timer.start()

            try:
                result: Any = func(*args, **kwargs)
            finally:
                timer.cancel()

            return result
        return inner
    return outer


# just to make sure the user hasn't broken anything
def validate_settings():
    try:
        settings()
    except yaml.YAMLError as error:
        error_tabbed: str = str(error).replace('\n', '\n    ')
        print(f"Couldn't parse settings:\n    {error_tabbed}")
        raise SystemExit

    setting_count: int = 25
    tas_path: str = str(settings()['tas_path'])
    bool_settings = ('exit_game_when_done', 'clear_output_log_on_startup', 'open_tas_when_done', 'extra_attempts', 'keep_celeste_focused',
                     'ensure_breakpoint_end', 'auto_trim', 'restart_crashed_game', 'kill_notepads', 'optimize_feathers', 'session_alt_timeout_method')
    int_settings = ('extra_attempts_window_size', 'feather_degree_window_size')
    num_settings = ('loading_time_compensation', 'focus_wait_timeout', 'session_short_timeout', 'session_long_timeout', 'session_interval', 'restart_prewait',
                    'restart_postwait', 'session_wait')  # int or float

    # makes sure that each setting is what type it needs to be, and some other checks as well
    if not os.path.isfile(tas_path):
        invalid_setting(f"TAS file \"{tas_path}\" doesn't exist")
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
    if len(settings()) != setting_count:
        invalid_setting(f"Wrong number of settings ({len(settings())} != {setting_count})")


def invalid_setting(error_message: str):
    print(f"Settings loading error: {error_message}")
    raise SystemExit


def pluralize(count: Union[int, Sized]) -> str:
    if isinstance(count, int):
        return 's' if count != 1 else ''
    else:
        return 's' if len(count) != 1 else ''


@functools.cache
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
