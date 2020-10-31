import math
import os
import random
import sys
import time

try:
    import tqdm
except ImportError:
    tqdm = None


def main():
    # configuration
    frames: int = 10
    permutations: int = 100000
    x_init: float = 0.0
    speed_x_init: float = 0.0
    goal_position: float = 0.0
    goal_direction: str = '-'  # - means approaching from the left, + is from the right
    goal_speed: float = 90.0  # this is calculated by abs(final speed - goal speed)
    prioritize_speed: bool = False  # sort by speed instead of position
    ducking: bool = False
    on_ground: bool = False
    cold_core: bool = False
    holdable_slow: bool = False
    holdable_slow_fall: bool = False
    in_space: bool = False
    delta_time: float = 1/60

    start_time = time.perf_counter()
    sys.stdout = Logger()
    print("building permutations...")
    if not tqdm:
        print("(install tqdm to have progress bars if you like)")
    input_permutations = build_input_permutations(frames, permutations)
    valid_permutations = []
    print("\nsimulating inputs...")

    if tqdm:
        input_permutations_iter = tqdm.tqdm(input_permutations, ncols=100)
    else:
        input_permutations_iter = input_permutations

    for permutation in input_permutations_iter:
        x: float = x_init
        speed_x: float = speed_x_init

        for input_line in permutation:
            inputs = [input_line[1]] * input_line[0]

            for input_key in inputs:
                # get inputs first
                move_x: float = {'l': -1.0, '': 0.0, 'r': 1.0}[input_key]
                
                # celeste code (from Player.NormalUpdate and Actor.MoveH) somewhat loosely translated from C# to python

                # calculate speed second
                if ducking and on_ground:
                    speed_x = approach(speed_x, 0.0, 500 * delta_time)
                else:
                    num1: float = 1 if on_ground else 0.65

                    if on_ground and cold_core:
                        num1 *= 0.3

                    # ignored low friction variant stuff

                    if holdable_slow:
                        num2: float = 70.0
                    elif holdable_slow_fall and not on_ground:
                        num2 = 108.0
                        num1 *= 0.5
                    else:
                        num2 = 90.0

                    if in_space:
                        num2 *= 0.6

                    if abs(speed_x) <= num2 or (0.0 if speed_x == 0.0 else math.copysign(1, speed_x)) != move_x:
                        speed_x = approach(speed_x, num2 * move_x, 1000 * num1 * delta_time)
                    else:
                        speed_x = approach(speed_x, num2 * move_x, 400 * num1 * delta_time)

                # calculate position third
                x += speed_x * delta_time

        if (goal_direction == '-' and x < goal_position) or (goal_direction == '+' and x > goal_position):
            append_permutation = True

            for valid_permutation in valid_permutations:
                if x == valid_permutation[0] and speed_x == valid_permutation[1]:
                    if len(permutation) < len(valid_permutation[2]):
                        valid_permutations.remove(valid_permutation)
                    else:
                        append_permutation = False
                        break

            if append_permutation:
                valid_permutations.append((x, speed_x, permutation))

    if prioritize_speed:
        valid_permutations.sort(reverse=goal_direction == '+', key=lambda p: p[0])
        valid_permutations.sort(reverse=goal_direction == '-', key=lambda p: abs(p[1] - goal_speed))
    else:
        valid_permutations.sort(reverse=goal_direction == '-', key=lambda p: abs(p[1] - goal_speed))
        valid_permutations.sort(reverse=goal_direction == '+', key=lambda p: p[0])

    print("\ndone, outputting (useful inputs are at the bottom btw)\n")
    end_time = time.perf_counter()

    for valid_permutation in valid_permutations:
        print(valid_permutation)

    print(f"\nframes: {frames}")
    print(f"total permutations: {len(input_permutations)}")
    print(f"shown permutations: {len(valid_permutations)}")
    print(f"processing time: {round(end_time - start_time, 3)} s")


def approach(val: float, target: float, max_move: float):
    if val <= target:
        return min(val + max_move, target)
    else:
        return max(val - max_move, target)


def build_input_permutations(frame_limit: int, perms: int):
    input_permutations = []

    if tqdm:
        reps = tqdm.tqdm(range(perms), ncols=100)
    else:
        reps = range(perms)

    for _ in reps:
        inputs = []
        frame_counter = 0

        while frame_counter < frame_limit:
            frames = round(random.randint(1, frame_limit - frame_counter))
            frame_counter += frames
            inputs.append((frames, random.choice(('l', '', 'r'))))

        input_permutations.append(inputs)

    return input_permutations


# log all prints to a file
class Logger(object):
    def __init__(self):
        if os.path.isfile('out.txt'):
            os.remove('out.txt')

        self.terminal = sys.stdout
        self.log = open('out.txt', 'a')

    def write(self, message):
        self.terminal.write(message)
        self.log.write(message)
        self.log.flush()

    def flush(self):
        pass


if __name__ == '__main__':
    main()
