# this is more translated movement code, but it loops infinitely and seems replaceable with a simple +=


# move_x: float = 0.0
# move_counter_x: float = 0
#
# move_h: float = speed_x * delta_time
# move_counter_x += move_h
# move_h1: int = round(move_counter_x)
#
# if move_h1 == 0:
#     move_counter_x -= float(move_h1)
#     num3: int = 0 if move_h == 0 else math.copysign(1, move_h)
#     num4: int = 0
#
#     while move_h != 0.0:
#         num4 += num3
#         move_h -= num3
#         x += num3

# -----------------------------------------------------------------------------------------------

# this is a more proper permutation generator that actually uses itertools.permutations,
# buuut it's slower and worse than just randomly brute forcing it lol


# permutation_limit = 10_000_000 / frame_limit
# # to clarify, limit here means permutation count for an input line length,
# # whereas for input_permutations_limited, it means frames
#
# possible_input_lines = []
# input_permutations_limited = []
#
# for frame_num in range(1, frame_limit + 1):
#     possible_input_lines.extend(((frame_num, 'l'), (frame_num, ''), (frame_num, 'r')))
#
# # possible_input_lines = tuple(reversed(possible_input_lines))
#
# if tqdm:
#     frame_range = tqdm.tqdm(range(1, frame_limit + 1), ncols=100)
# else:
#     frame_range = range(1, frame_limit + 1)
#
# for input_num in frame_range:
#     if input_num == 10:
#         print()
#
#     random.shuffle(possible_input_lines)  # ewwwww (but helps)
#     input_permutations = itertools.permutations(tuple(possible_input_lines), input_num)
#     permutation_count = 0
#
#     for input_permutation in input_permutations:
#         frame_sum = 0
#
#         for input_line in input_permutation:
#             frame_sum += int(input_line[0])
#
#         if frame_sum == frame_limit:
#             input_permutations_limited.append(input_permutation)
#
#         permutation_count += 1
#         if permutation_count >= permutation_limit:
#             break
#
# return input_permutations_limited