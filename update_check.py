import datetime
import json
import os
import time
from typing import Tuple, Union, Sized

import requests


def is_latest_commit():
    outdated = False

    if time.time() - save_data.last_checked > save_data.check_interval:
        try:
            commit_hash = get_latest_commit(save_data.short_timeout)[0]
        except (requests.Timeout, requests.exceptions.ReadTimeout):
            print(f"Timed out getting latest commmit after {save_data.short_timeout} seconds\n")
            return
        except (requests.RequestException, requests.ConnectionError) as error:
            print(f"Error getting latest commmit: {error}\n")
            return

        outdated = commit_hash != save_data.this_commit
        save_data.update_last_checked(outdated)

    if outdated or save_data.was_outdated:
        time_since_commit = datetime.datetime.now(datetime.timezone.utc) - datetime.datetime.fromtimestamp(save_data.this_commit_time, tz=datetime.timezone.utc)

        if time_since_commit.days > 0:
            time_since_commit_formatted = f"{time_since_commit.days} day{plural(time_since_commit.days)}"
        else:
            hours_since_commit = int(time_since_commit.seconds / 3600)
            time_since_commit_formatted = f"{hours_since_commit} hour{plural(hours_since_commit)}"

        print(f"WARNING: Radeline is {time_since_commit_formatted} out of date, please download the latest version from:\n"
              "    https://nightly.link/Kataiser/radeline/workflows/build/master/Radeline.zip\n"
              "See what's been changed:\n"
              "    https://github.com/Kataiser/radeline/commits\n")


def get_latest_commit(timeout: int) -> Tuple[str, int]:
    commit_request = requests.get('https://api.github.com/repos/Kataiser/radeline/commits?per_page=1', timeout=timeout, params={'accept': 'application/vnd.github.v3+json'})
    commit_request_json = commit_request.json()[0]
    commit_time = datetime.datetime.fromisoformat(commit_request_json['commit']['author']['date'])
    return commit_request_json['sha'], round(commit_time.timestamp())


class SaveData:
    def __init__(self):
        data_paths = [os.path.abspath(path) for path in ('updater_data.json', '..\\resources\\updater_data.json', '..\\updater_data.json')]
        self.data_path = [path for path in data_paths if os.path.isfile(path)][0]
        save_data_read = self.read()

        self.this_commit = save_data_read['save']['this_commit']
        self.last_checked = save_data_read['save']['last_checked']
        self.was_outdated = save_data_read['save']['was_outdated']
        self.short_timeout = save_data_read['settings']['short_timeout']
        self.long_timeout = save_data_read['settings']['long_timeout']
        self.check_interval = save_data_read['settings']['check_interval']

        try:
            self.this_commit_time = save_data_read['save']['this_commit_time']
        except KeyError:
            self.this_commit_time = 0

    def update_latest_commit(self, path):
        self.data_path = path
        latest_commit = get_latest_commit(save_data.long_timeout)
        out = {'save': {'last_checked': 0, 'was_outdated': False}, 'settings': {'short_timeout': 3, 'long_timeout': 10, 'check_interval': 1800}}
        out['save']['this_commit'] = latest_commit[0]
        out['save']['this_commit_time'] = latest_commit[1]
        self.write(out)

    def update_last_checked(self, was_outdated):
        out = self.read()
        out['save']['last_checked'] = int(time.time())
        out['save']['was_outdated'] = was_outdated
        self.write(out)

    def read(self):
        with open(self.data_path, 'r', encoding='UTF8', errors='replace') as save_data_json:
            return json.load(save_data_json)

    def write(self, data):
        with open(self.data_path, 'w', encoding='UTF8') as save_data_json:
            json.dump(data, save_data_json, indent=4, ensure_ascii=False)


def plural(count: Union[int, Sized]) -> str:
    if isinstance(count, int):
        return 's' if count != 1 else ''
    else:
        return 's' if len(count) != 1 else ''


save_data = SaveData()


if __name__ == '__main__':
    is_latest_commit()
