import json
import os
import time

import requests


def is_latest_commit():
    outdated = False

    if time.time() - save_data.last_checked > save_data.check_interval:
        try:
            commit_hash = get_latest_commit(save_data.short_timeout)
        except (requests.Timeout, requests.exceptions.ReadTimeout):
            print(f"Timed out getting latest commmit after {save_data.short_timeout} seconds\n")
            return
        except (requests.RequestException, requests.ConnectionError) as error:
            print(f"Error getting latest commmit: {error}\n")
            return

        outdated = commit_hash != save_data.this_commit
        save_data.update_last_checked(outdated)

    if outdated or save_data.was_outdated:
        print("WARNING: Radeline is out of date, please download the latest version from:\n"
              "    https://nightly.link/Kataiser/radeline/workflows/build/master/Radeline.zip\n"
              "See what's been changed:\n"
              "    https://github.com/Kataiser/radeline/commits\n")


def get_latest_commit(timeout: int) -> str:
    commit_request = requests.get('https://api.github.com/repos/Kataiser/radeline/commits?per_page=1', timeout=timeout, params={'accept': 'application/vnd.github.v3+json'})
    return commit_request.json()[0]['sha']


class SaveData:
    def __init__(self):
        self.data_path = 'updater_data.json'
        if not os.path.isfile(self.data_path):
            self.data_path = os.path.abspath('..\\resources\\updater_data.json')

        save_data_read = self.read()

        self.this_commit = save_data_read['save']['this_commit']
        self.last_checked = save_data_read['save']['last_checked']
        self.was_outdated = save_data_read['save']['was_outdated']
        self.short_timeout = save_data_read['settings']['short_timeout']
        self.long_timeout = save_data_read['settings']['long_timeout']
        self.check_interval = save_data_read['settings']['check_interval']

    def update_latest_commit(self, path):
        self.data_path = path
        latest_commit = get_latest_commit(save_data.long_timeout)
        out = self.read()
        out['save']['this_commit'] = latest_commit
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


save_data = SaveData()


if __name__ == '__main__':
    is_latest_commit()
