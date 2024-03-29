import gc
import itertools
import math
import os
import platform
import random
import sys
import time
from typing import Callable, List, Optional, Set, Tuple, Union

import tqdm
import yaml

import input_formatter
import update_check


class Config:
    def __init__(self):
        with open('config.yaml', 'r') as config_file:
            cfg_dict = yaml.safe_load(config_file)
            self.mtime = os.path.getmtime('config.yaml')

        # yes this is awkward but I don't care
        self.frames: int = int(cfg_dict['frames'])
        self.permutations: int = int(cfg_dict['permutations'])
        self.axis: str = str(cfg_dict['axis'])
        self.jump_timer: int = int(cfg_dict['jump_timer'])
        self.goal_speed: float = float(cfg_dict['goal_speed'])
        self.filter_min: float = float(min(cfg_dict['filter']))
        self.filter_max: float = float(max(cfg_dict['filter']))
        self.prioritize_speed: bool = bool(cfg_dict['prioritize_speed'])
        self.holding: bool = bool(cfg_dict['holding'])
        self.auto_jump: bool = bool(cfg_dict['auto_jump'])
        self.append_keys: str = str(cfg_dict['append_keys'])
        self.open_results: bool = bool(cfg_dict['open_results'])
        self.hide_duplicates: bool = bool(cfg_dict['hide_duplicates'])
        self.silent_output: bool = bool(cfg_dict['silent_output'])
        self.triangular_random: bool = bool(cfg_dict['triangular_random'])
        self.rng_threshold: int = int(cfg_dict['rng_threshold'])
        self.rng_threshold_slow: int = int(cfg_dict['rng_threshold_slow'])
        self.disabled_key: Optional[str] = str(cfg_dict['disabled_key']).lower()
        self.max_fall: float = float(cfg_dict['max_fall'])
        self.on_ground: bool = bool(cfg_dict['on_ground'])
        self.ram_check: bool = bool(cfg_dict['ram_check'])
        self.append_keys: str = str(cfg_dict['append_keys'])
        self.retained: bool = bool(cfg_dict['retained'])

        if self.axis not in ('x', 'y'):
            print("Axis must be x or y, exiting")
            raise SystemExit
        if len(cfg_dict['filter']) != 2:
            print("Filter must be two elements, exiting")
            raise SystemExit
        if self.disabled_key not in ('auto', 'l', 'r', 'j', 'd', 'none'):
            print("Disabled key must be auto, l, r, j, d, or just blank, exiting")
            raise SystemExit

        for append_key in self.append_keys:
            if self.axis == 'x' and append_key.lower() in ('l', 'r'):
                print(f"Can't have {append_key} in append_keys when axis is X, exiting")
                raise SystemExit
            elif self.axis == 'y' and append_key.lower() in ('j', 'd'):
                print(f"Can't have {append_key} in append_keys when axis is Y, exiting")
                raise SystemExit

        init_state = cfg_dict['init_state'].strip().split()
        axis_offset = 0 if self.axis == 'x' else 1
        self.pos_init: float = float(init_state[1 + axis_offset].rstrip(','))
        self.speed_init: float = float(init_state[4 + axis_offset].rstrip(','))
        self.auto_jump = 'AutoJump: True' in cfg_dict['init_state'] if 'AutoJump:' in cfg_dict['init_state'] else self.auto_jump
        self.max_fall = float(init_state[init_state.index('MaxFall:') + 1]) if 'MaxFall:' in cfg_dict['init_state'] else self.max_fall
        self.jump_timer = max(int(init_state[init_state.index('JumpTimer:') + 1]) - 1, 0) if 'JumpTimer:' in cfg_dict['init_state'] else self.jump_timer
        self.holding = 'Holding: Celeste.Holdable' in init_state if 'Holding:' in init_state else self.holding

        if self.axis == 'x' and self.retained:
            for i in range(len(init_state)):
                if init_state[i].startswith('Retained('):
                    self.speed_init = float(init_state[i + 1])
                    print(f"Assuming retained speed ({self.speed_init:.3f}) applies next frame")
                    break


def main():
    config_mtime = sim_main(True)

    while True:
        input_formatter.main(config_mtime)
        config_mtime = sim_main(False)


def sim_main(do_update_check: bool) -> float:
    if do_update_check:
        update_check.is_latest_commit()

    start_time: float = time.perf_counter()
    sys.stdout = Logger()
    cfg: Config = Config()

    if cfg.disabled_key in ('auto', 'none'):
        cfg.disabled_key = None

        # do some math to determine if a key can ever affect movement
        if cfg.axis == 'x':
            # disable holding backwards if speed can't ever drop below zero due to friction
            if (not cfg.on_ground and abs(cfg.speed_init) > cfg.frames * 65 / 6) or (cfg.on_ground and abs(cfg.speed_init) > cfg.frames * 50 / 3):
                cfg.disabled_key = 'l' if cfg.speed_init > 0 else 'r'
        else:
            # disable jump if past jump peak, or down if can't ever reach fast fall speed
            if cfg.speed_init > 40:
                cfg.disabled_key = 'j'
            elif cfg.speed_init + cfg.frames * 15 <= 160:
                cfg.disabled_key = 'd'
    elif (cfg.axis == 'x' and cfg.disabled_key not in ('l', 'r', 'd')) or (cfg.axis == 'y' and cfg.disabled_key not in ('j', 'd')):
        print(f"Didn't disable {cfg.disabled_key.upper()} key since it wouldn't have been generated anyway\n")
        cfg.disabled_key = None

    if cfg.disabled_key:
        print(f"Disabled generating {cfg.disabled_key.upper()} inputs\n")

    generated_keys_len = len(generator_keys(cfg))

    if generated_keys_len == 3:
        rng_threshold = cfg.rng_threshold_slow
    elif generated_keys_len == 4:
        rng_threshold = cfg.rng_threshold_slow - 2
    else:
        rng_threshold = cfg.rng_threshold

    use_sequential = cfg.frames < rng_threshold

    if use_sequential:
        print("Building permutations using sequential method...")
        input_permutations: Union[List[tuple], Set[tuple]] = build_input_permutations_sequential(cfg)
    else:
        print("Building permutations using RNG method...")
        input_permutations = build_input_permutations_rng(cfg)

    # store as positions and speed dict, for performance
    valid_permutations: dict = {}
    output_permutations: List[Tuple[float, float, tuple]] = []
    speeds: set = set()
    permutation: tuple
    print("\nSimulating inputs...")

    for permutation in tqdm.tqdm(input_permutations, ncols=100):
        results_pos: float
        results_speed: float
        sim_function: Callable = sim_x if cfg.axis == 'x' else sim_y
        results_pos, results_speed = sim_function(permutation, cfg)

        # if result within filter range
        if cfg.filter_min <= results_pos <= cfg.filter_max:
            if results_pos not in valid_permutations:
                valid_permutations[results_pos] = {}

            if results_speed in valid_permutations[results_pos]:
                append_permutation: bool = True
                prev_permutations = valid_permutations[results_pos][results_speed]

                if cfg.hide_duplicates:
                    for prev_permutation in prev_permutations:
                        if len(permutation) < len(prev_permutation):
                            prev_permutations.remove(prev_permutation)
                        else:
                            append_permutation = False
                            break

                if append_permutation:
                    prev_permutations.append(permutation)
                    speeds.add(results_speed)
            else:
                valid_permutations[results_pos][results_speed] = [permutation]
                speeds.add(results_speed)

    # memory cleanup 1
    input_permutations_len: int = len(input_permutations)
    del input_permutations
    gc.collect()

    # convert optimized dict to sorted list
    if cfg.prioritize_speed:
        sorted_positions = sorted(valid_permutations)

        for speed in sorted(speeds, reverse=True, key=lambda s: abs(s - cfg.goal_speed)):
            for position in sorted_positions:
                if speed in valid_permutations[position]:
                    for permutation in valid_permutations[position][speed]:
                        output_permutations.append((position, speed, permutation))
    else:
        for position in sorted(valid_permutations):
            for speed in sorted(valid_permutations[position], reverse=True, key=lambda s: abs(s - cfg.goal_speed)):
                for permutation in valid_permutations[position][speed]:
                    output_permutations.append((position, speed, permutation))

    # memory cleanup 2
    del valid_permutations
    gc.collect()

    print("\nDone, outputting\n")
    sys.stdout.print_enabled = not cfg.silent_output

    # format and print permutations, which also saves them to the results file
    for valid_permutation in output_permutations:
        perm_display: List[List[Union[int, str]]] = []

        for input_line in valid_permutation[2]:
            if perm_display and perm_display[-1][1] == input_line[1]:
                perm_display[-1][0] += input_line[0]
            else:
                perm_display.append(list(input_line))

        print(f'{valid_permutation[:2]} {perm_display}')

    # memory cleanup 3
    valid_permutations_len: int = len(output_permutations)
    del output_permutations
    gc.collect()

    print("")
    sys.stdout.print_enabled = True
    if not use_sequential:
        print(f"Intended permutations: {cfg.permutations}")
    print(f"Generated permutations: {input_permutations_len}")
    print(f"Shown permutations: {valid_permutations_len}")
    print(f"Processing time: {round(time.perf_counter() - start_time, 1)} s\n")

    if cfg.open_results and platform.system() == 'Windows':
        # opens in default text editor
        os.startfile(sys.stdout.filename)

    sys.stdout = sys.__stdout__
    return cfg.mtime


# simulate X axis inputs
def sim_x(inputs: tuple, cfg: Config) -> Tuple[float, float]:
    x: float = cfg.pos_init
    speed_x: float = cfg.speed_init
    input_line: Tuple[int, str]
    mult1: float = 0.0166667 * 1000 if cfg.on_ground else 0.65 * 0.0166667 * 1000
    mult2: float = 0.0166667 * 400 if cfg.on_ground else 0.65 * 0.0166667 * 400
    grounded = cfg.on_ground

    if cfg.holding:
        max_: float = 70.0
    else:
        max_ = 90.0

    for input_line in inputs:
        input_frames: List[str] = [input_line[1]] * input_line[0]
        input_key: str

        for input_key in input_frames:
            # celeste code (from Player.NormalUpdate) somewhat loosely translated from C# to python

            if grounded and input_key == 'd':
                speed_x = approach(speed_x, 0.0, 500 * 0.0166667)
            else:
                # get inputs first
                move_x: float = {'l': -1.0, '': 0.0, 'r': 1.0}[input_key]

                # calculate speed second
                if abs(speed_x) <= max_ or (0.0 if speed_x == 0.0 else float(math.copysign(1, speed_x))) != move_x:
                    speed_x = approach(speed_x, max_ * move_x, mult1)
                else:
                    speed_x = approach(speed_x, max_ * move_x, mult2)

            # calculate position third
            x += speed_x * 0.0166667

    return float(round(x, 10)), float(round(speed_x, 10))


# simulate Y axis inputs
def sim_y(inputs: tuple, cfg: Config) -> Tuple[float, float]:
    y: float = cfg.pos_init
    speed_y: float = cfg.speed_init
    max_fall: float = cfg.max_fall
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
                max_fall = approach(max_fall, 240.0, 300 * 0.0166667)
            else:
                max_fall = approach(max_fall, 160.0, 300 * 0.0166667)

            if abs(speed_y) <= 40.0 and (input_key == 'j' or cfg.auto_jump):
                mult = 900 * 0.5 * 0.0166667
            else:
                mult = 900 * 0.0166667

            speed_y = approach(speed_y, max_fall, mult)

            if jump_timer > 0:
                if input_key == 'j' or cfg.auto_jump:
                    speed_y = min(speed_y, cfg.speed_init)
                else:
                    jump_timer = 0

            jump_timer -= 1

            # calculate position third
            y += speed_y * 0.0166667

    return float(round(y, 10)), float(round(speed_y, 10))


# from Monocle.Calc
def approach(val: float, target: float, max_move: float) -> float:
    if val <= target:
        return min(val + max_move, target)
    else:
        return max(val - max_move, target)


# generate every possible input permutation sequentially
def build_input_permutations_sequential(cfg: Config) -> List[tuple]:
    input_permutations: List[tuple] = []
    keys: Tuple[str, ...] = generator_keys(cfg)
    permutation_count: int = len(keys) ** cfg.frames
    permutation: Tuple[str, ...]
    broke_from_loop: bool = False
    ram_check_iter: int = 0
    do_ram_check: bool = permutation_count > 3000000 and cfg.ram_check
    process: Optional = current_process_if_needed(do_ram_check)

    # all hail itertools.product()
    for permutation in tqdm.tqdm(itertools.product(keys, repeat=cfg.frames), total=permutation_count, ncols=100):
        permutation_formatted: List[Tuple[int, str]] = []
        current_input: str = permutation[0]
        input_len: int = 0
        frame_key: str

        # convert messy inputs to the compact format
        for frame_key in permutation:
            if frame_key == current_input:
                input_len += 1
            else:
                permutation_formatted.append((input_len, current_input))
                current_input = frame_key
                input_len = 1

        permutation_formatted.append((input_len, current_input))
        input_permutations.append(tuple(permutation_formatted))
        ram_check_iter += 1

        if do_ram_check and ram_check_iter > 100000:
            ram_check_iter = 0

            if hit_ram_limit(process):
                broke_from_loop = True
                break

    if broke_from_loop:
        print("Exiting generating inputs early due to running low on RAM")

    return input_permutations


# generate a ton of input permutations randomly
def build_input_permutations_rng(cfg: Config) -> Set[tuple]:
    input_permutations: Set[tuple] = set()  # is a set to avoid duplicates, which takes a perfomance hit
    triangular: bool = cfg.triangular_random
    keys: Tuple[str, ...] = generator_keys(cfg)
    max_permutations: int = len(keys) ** cfg.frames
    broke_from_loop_max: bool = False
    broke_from_loop_ram: bool = False
    ram_check_iter: int = 0
    do_ram_check: bool = min(cfg.permutations, max_permutations) > 5000000 and cfg.ram_check
    process: Optional = current_process_if_needed(do_ram_check)

    for _ in tqdm.trange(cfg.permutations, ncols=100):
        inputs: List[Tuple[int, str]] = []
        frame_counter = 0

        while frame_counter < cfg.frames:
            if triangular:
                # probably don't actually use this, idk
                frames = round(random.triangular(1, cfg.frames - frame_counter, 1))
            else:
                frames = round(random.randint(1, cfg.frames - frame_counter))

            frame_counter += frames
            inputs.append((frames, random.choice(keys)))

        input_permutations.add(tuple(inputs))
        ram_check_iter += 1

        if do_ram_check and ram_check_iter > 100000:
            ram_check_iter = 0

            if hit_ram_limit(process):
                broke_from_loop_ram = True
                break

        if len(input_permutations) >= max_permutations:
            broke_from_loop_max = True
            break

    if broke_from_loop_ram:
        print("Exiting generating inputs early due to running low on RAM")

    if broke_from_loop_max:
        print(f"Exiting generating early due to reaching max possible permutations ({max_permutations})")

    return input_permutations


# determine which keys will be generated
def generator_keys(cfg: Config) -> Tuple[str, ...]:
    if cfg.axis == 'x':
        keys = ['', 'l', 'r']

        if cfg.on_ground:
            keys.append('d')
    else:
        keys = ['', 'j', 'd']

    if cfg.disabled_key:
        keys.remove(cfg.disabled_key)

    return tuple(keys)


# only import psutil and get current process if RAM checking will be done at all
def current_process_if_needed(doing_ram_check: bool) -> Optional:
    if doing_ram_check:
        import psutil
        return psutil.Process()


# determinte if either the process is reaching the 32-bit limit or the machine is low on memory
def hit_ram_limit(process) -> bool:
    import psutil
    return process.memory_info().rss > 1_800_000_000 or psutil.virtual_memory().available < 200_000_000


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
