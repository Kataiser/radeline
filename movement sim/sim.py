import gc
import itertools
import math
import os
import platform
import random
import sys
import time
from typing import List, Set, Tuple, Union

import tqdm
import yaml

import input_formatter


class Config:
    def __init__(self):
        with open('config.yaml', 'r') as config_file:
            cfg_dict = yaml.safe_load(config_file)

        # yes this is awkward but I don't care
        self.frames: int = int(cfg_dict['frames'])
        self.permutations: int = int(cfg_dict['permutations'])
        self.axis: str = str(cfg_dict['axis'])
        self.jump_timer: int = int(cfg_dict['jump_timer'])
        self.jump_speed: float = float(cfg_dict['jump_speed'])
        self.goal_position: float = float(cfg_dict['goal_position'])
        self.goal_direction: str = str(cfg_dict['goal_direction'])
        self.goal_speed: float = float(cfg_dict['goal_speed'])
        self.prioritize_speed: bool = bool(cfg_dict['prioritize_speed'])
        self.on_ground: bool = bool(cfg_dict['on_ground'])
        self.holding: bool = bool(cfg_dict['holding'])
        self.auto_jump: bool = bool(cfg_dict['auto_jump'])
        self.append_keys: str = str(cfg_dict['append_keys'])
        self.open_results: bool = bool(cfg_dict['open_results'])
        self.hide_duplicates: bool = bool(cfg_dict['hide_duplicates'])
        self.silent_output: bool = bool(cfg_dict['silent_output'])
        self.triangular_random: bool = bool(cfg_dict['triangular_random'])
        self.rng_threshold: int = int(cfg_dict['rng_threshold'])

        if self.axis not in ('x', 'y'):
            print("Axis must be x or y, exiting")
            raise SystemExit
        if self.goal_direction not in ('-', '+'):
            print("Goal direction must be - or +, exiting")
            raise SystemExit

        init_state = str(cfg_dict['init_state']).strip().split()
        axis_offset = 0 if self.axis == 'x' else 1
        self.pos_init: float = float(init_state[1 + axis_offset].rstrip(','))
        self.speed_init: float = float(init_state[4 + axis_offset].rstrip(','))


def main():
    start_time = time.perf_counter()
    sys.stdout = Logger()
    cfg: Config = Config()
    use_sequential: bool = cfg.frames < cfg.rng_threshold

    if use_sequential:
        print("Building permutations using sequential method...")
        input_permutations: Union[List[tuple], Set[tuple]] = build_input_permutations_sequential(cfg)
    else:
        print("Building permutations using RNG method...")
        input_permutations = build_input_permutations_rng(cfg)

    valid_permutations: List[Tuple[float, float, tuple]] = []
    permutation: tuple
    print("\nSimulating inputs...")

    for permutation in tqdm.tqdm(input_permutations, ncols=100):
        results_pos: float
        results_speed: float

        if cfg.axis == 'x':
            results_pos, results_speed = sim_x(permutation, cfg)
        else:
            results_pos, results_speed = sim_y(permutation, cfg)

        if (cfg.goal_direction == '-' and results_pos < cfg.goal_position) or (cfg.goal_direction == '+' and results_pos > cfg.goal_position):
            append_permutation: bool = True
            valid_permutation: Tuple[float, float, tuple]

            if cfg.hide_duplicates:
                for valid_permutation in valid_permutations:
                    if results_pos == valid_permutation[0] and results_speed == valid_permutation[1]:
                        if len(permutation) < len(valid_permutation[2]):
                            valid_permutations.remove(valid_permutation)
                        else:
                            append_permutation = False
                            break

            if append_permutation:
                valid_permutations.append((results_pos, results_speed, permutation))

    if cfg.prioritize_speed:
        valid_permutations.sort(reverse=cfg.goal_direction == '+', key=lambda p: p[0])
        valid_permutations.sort(reverse=True, key=lambda p: abs(p[1] - cfg.goal_speed))
    else:
        valid_permutations.sort(reverse=True, key=lambda p: abs(p[1] - cfg.goal_speed))
        valid_permutations.sort(reverse=cfg.goal_direction == '+', key=lambda p: p[0])

    input_permutations_len: int = len(input_permutations)
    del input_permutations
    gc.collect()

    print("\nDone, outputting\n")
    sys.stdout.print_enabled = not cfg.silent_output

    for valid_permutation in valid_permutations:
        perm_display: List[List[Union[int, str]]] = []

        for input_line in valid_permutation[2]:
            if perm_display and perm_display[-1][1] == input_line[1]:
                perm_display[-1][0] += input_line[0]
            else:
                perm_display.append(list(input_line))

        print(f'{valid_permutation[:2]} {perm_display}')

    valid_permutations_len: int = len(valid_permutations)
    del valid_permutations
    gc.collect()

    print()
    sys.stdout.print_enabled = True
    if not use_sequential:
        print(f"Intended permutations: {cfg.permutations}")
    print(f"Generated permutations: {input_permutations_len}")
    print(f"Shown permutations: {valid_permutations_len}")
    print(f"Processing time: {round(time.perf_counter() - start_time, 1)} s\n")

    if cfg.open_results and platform.system() == 'Windows':
        os.startfile(sys.stdout.filename)

    sys.stdout = sys.__stdout__
    input_formatter.main()


def sim_x(inputs: tuple, cfg: Config) -> Tuple[float, float]:
    x: float = cfg.pos_init
    speed_x: float = cfg.speed_init
    input_line: Tuple[int, str]
    mult: float = 1.0 if cfg.on_ground else 0.65

    if cfg.holding:
        max_: float = 70.0
    else:
        max_ = 90.0

    for input_line in inputs:
        input_frames: List[str] = [input_line[1]] * input_line[0]
        input_key: str

        for input_key in input_frames:
            # celeste code (from Player.NormalUpdate) somewhat loosely translated from C# to python

            # get inputs first
            move_x: float = {'l': -1.0, '': 0.0, 'r': 1.0}[input_key]

            # calculate speed second
            if abs(speed_x) <= max_ or (0.0 if speed_x == 0.0 else float(math.copysign(1, speed_x))) != move_x:
                speed_x = approach(speed_x, max_ * move_x, 1000.0 / 60.0 * mult)
            else:
                speed_x = approach(speed_x, max_ * move_x, 400.0 / 60.0 * mult)

            # calculate position third
            x += speed_x / 60.0

    return float(round(x, 10)), float(round(speed_x, 10))


def sim_y(inputs: tuple, cfg: Config) -> Tuple[float, float]:
    y: float = cfg.pos_init
    speed_y: float = cfg.speed_init
    max_fall: float = max(160.0, cfg.speed_init)
    jump_timer: int = cfg.jump_timer
    input_line: Tuple[int, str]

    for input_line in inputs:
        input_frames: List[str] = [input_line[1]] * input_line[0]
        input_key: str

        for input_key in input_frames:
            # celeste code (from Player.NormalUpdate) somewhat loosely translated from C# to python

            # get inputs first
            move_y: int = {'j': 0, '': 0, 'd': 1}[input_key]

            # calculate speed second
            if move_y == 1 and speed_y >= 160.0:
                max_fall = approach(max_fall, 240.0, 300.0 / 60.0)
            else:
                max_fall = approach(max_fall, 160.0, 300.0 / 60.0)

            mult: float = 0.5 if (abs(speed_y) <= 40.0 and (input_key == 'j' or cfg.auto_jump)) else 1.0
            speed_y = approach(speed_y, max_fall, (900.0 * mult) / 60.0)

            if jump_timer > 0:
                if input_key == 'j' or cfg.auto_jump:
                    speed_y = min(speed_y, cfg.jump_speed)
                else:
                    jump_timer = 0

            jump_timer -= 1

            # calculate position third
            y += speed_y / 60.0

    return float(round(y, 10)), float(round(speed_y, 10))


def approach(val: float, target: float, max_move: float) -> float:
    if val <= target:
        return min(val + max_move, target)
    else:
        return max(val - max_move, target)


def build_input_permutations_sequential(cfg: Config) -> List[tuple]:
    input_permutations: List[tuple] = []
    keys: Tuple[str, str, str] = ('', 'r', 'l') if cfg.axis == 'x' else ('', 'd', 'j')
    permutation_count: int = 3 ** cfg.frames
    permutation: Tuple[str, ...]

    # permutation: object
    for permutation in tqdm.tqdm(itertools.product(keys, repeat=cfg.frames), total=permutation_count, ncols=100):
        permutation_formatted: List[Tuple[int, str]] = []
        current_input: str = permutation[0]
        input_len: int = 0
        frame_key: str

        for frame_key in permutation:
            if frame_key == current_input:
                input_len += 1
            else:
                permutation_formatted.append((input_len, current_input))
                current_input = frame_key
                input_len = 1

        permutation_formatted.append((input_len, current_input))
        input_permutations.append(tuple(permutation_formatted))

    return input_permutations


def build_input_permutations_rng(cfg: Config) -> Set[tuple]:
    input_permutations: Set[tuple] = set()
    triangular: bool = cfg.triangular_random
    keys: Tuple[str, str, str] = ('l', '', 'r') if cfg.axis == 'x' else ('j', '', 'd')

    for _ in tqdm.trange(cfg.permutations, ncols=100):
        inputs: List[Tuple[int, str]] = []
        frame_counter = 0

        while frame_counter < cfg.frames:
            if triangular:
                frames = round(random.triangular(1, cfg.frames - frame_counter, 1))
            else:
                frames = round(random.randint(1, cfg.frames - frame_counter))

            frame_counter += frames
            inputs.append((frames, random.choice(keys)))

        input_permutations.add(tuple(inputs))

    return input_permutations


# log all prints to a file
class Logger(object):
    def __init__(self):
        self.filename: str = 'results.txt'

        if os.path.isfile(self.filename):
            os.remove(self.filename)

        self.terminal = sys.stdout
        self.log = open(self.filename, 'a')
        self.print_enabled: bool = True

    def write(self, message):
        self.log.write(message)
        self.log.flush()

        if self.print_enabled:
            self.terminal.write(message)

    def flush(self):
        pass


if __name__ == '__main__':
    main()
