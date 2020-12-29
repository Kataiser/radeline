import gc
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
        self.ducking: bool = bool(cfg_dict['ducking'])
        self.on_ground: bool = bool(cfg_dict['on_ground'])
        self.cold_core: bool = bool(cfg_dict['cold_core'])
        self.holding: bool = bool(cfg_dict['holding'])
        self.in_space: bool = bool(cfg_dict['in_space'])
        self.auto_jump: bool = bool(cfg_dict['auto_jump'])
        self.append_keys: str = str(cfg_dict['append_keys'])
        self.open_results: bool = bool(cfg_dict['open_results'])
        self.hide_duplicates: bool = bool(cfg_dict['hide_duplicates'])

        if self.axis not in ('x', 'y'):
            print("Axis must be x or y, exiting")
            raise SystemExit
        if self.goal_direction not in ('-', '+'):
            print("Goal direction must be - or +, exiting")
            raise SystemExit

        init_state = str(cfg_dict['init_state']).strip().split()
        axis_index = 0 if self.axis == 'x' else 1
        self.pos_init: float = float(init_state[1].split(',')[axis_index])
        self.speed_init: float = float(init_state[3].split(',')[axis_index])


def main():
    start_time = time.perf_counter()
    sys.stdout = Logger()
    cfg: Config = Config()
    print("Building permutations...")
    input_permutations: tuple = build_input_permutations(cfg)
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
    print(f"\nIntended permutations: {cfg.permutations}")
    print(f"Generated permutations: {input_permutations_len}")
    print(f"Shown permutations: {valid_permutations_len}")
    print(f"Processing time: {round(time.perf_counter() - start_time, 3)} s\n")

    if cfg.open_results and platform.system() == 'Windows':
        os.startfile(sys.stdout.filename)

    sys.stdout = sys.__stdout__
    input_formatter.main()


def sim_x(inputs: tuple, cfg: Config) -> Tuple[float, float]:
    x: float = cfg.pos_init
    speed_x: float = cfg.speed_init
    input_line: Tuple[int, str]

    for input_line in inputs:
        input_frames: List[str] = [input_line[1]] * input_line[0]
        input_key: str

        for input_key in input_frames:
            # celeste code (from Player.NormalUpdate) somewhat loosely translated from C# to python

            # get inputs first
            move_x: float = {'l': -1.0, '': 0.0, 'r': 1.0}[input_key]

            # calculate speed second
            if cfg.ducking and cfg.on_ground:
                speed_x = approach(speed_x, 0.0, 500.0 / 60.0)
            else:
                mult: float = 1.0 if cfg.on_ground else 0.65

                if cfg.on_ground and cfg.cold_core:
                    mult *= 0.3

                # ignored low friction variant stuff

                if cfg.holding:
                    max_: float = 70.0
                else:
                    max_ = 90.0

                if cfg.in_space:
                    max_ *= 0.6

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
    max_fall: float = 160.0
    jump_timer: int = cfg.jump_timer
    input_line: Tuple[int, str]

    for input_line in inputs:
        input_frames: List[str] = [input_line[1]] * input_line[0]
        input_key: str

        for input_key in input_frames:
            # celeste code (from Player.NormalUpdate) somewhat loosely translated from C# to python

            # get inputs first
            move_y: int = {'j': 0, '': 0, 'd': 1}[input_key]
            jumping: bool = input_key == 'j'

            # calculate speed second
            mf: float = 160.0
            fmf: float = 240.0

            if cfg.in_space:
                mf *= 0.6
                fmf *= 0.6

            # ignored some weird holdable stuff

            if move_y == 1 and speed_y >= mf:
                max_fall = approach(max_fall, fmf, 300.0 / 60.0)
            else:
                max_fall = approach(max_fall, mf, 300.0 / 60.0)

            # this line was kinda translated more using my experience from TASing than from actually translating the code so it may be wrong
            mult: float = 0.5 if (abs(speed_y) <= 40.0 and (jumping or cfg.auto_jump)) else 1.0

            if cfg.in_space:
                mult *= 0.6

            speed_y = approach(speed_y, max_fall, (900.0 * mult) / 60.0)

            if jump_timer > 0:
                if cfg.auto_jump or jumping:
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


def build_input_permutations(cfg: Config) -> tuple:
    input_permutations: Set[tuple] = set()

    if cfg.axis == 'x':
        keys: Tuple[str, str, str] = ('l', '', 'r')
    else:
        keys = ('j', '', 'd')

    for _ in tqdm.tqdm(range(cfg.permutations), ncols=100):
        inputs: List[Tuple[int, str]] = []
        frame_counter = 0

        while frame_counter < cfg.frames:
            frames = round(random.randint(1, cfg.frames - frame_counter))
            frame_counter += frames
            inputs.append((frames, random.choice(keys)))

        input_permutations.add(tuple(inputs))

    input_permutations_tuple: tuple = tuple(input_permutations)
    del input_permutations
    return input_permutations_tuple


# log all prints to a file
class Logger(object):
    def __init__(self):
        self.filename = 'results.txt'

        if os.path.isfile(self.filename):
            os.remove(self.filename)

        self.terminal = sys.stdout
        self.log = open(self.filename, 'a')

    def write(self, message):
        self.terminal.write(message)
        self.log.write(message)
        self.log.flush()

    def flush(self):
        pass


if __name__ == '__main__':
    main()
