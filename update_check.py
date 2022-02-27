import os

import requests


def is_latest_commit():
    try:
        commit_hash = get_latest_commit(3)
    except (requests.Timeout, requests.exceptions.ReadTimeout):
        print("Timed out getting latest commmit")
        return
    except (requests.RequestException, requests.ConnectionError):
        print("Couldn't get latest commmit")
        return

    if commit_hash != this_commit:
        print("Radeline is out of date, please download the latest version from:\n    https://nightly.link/Kataiser/radeline/workflows/build/master/Radeline.zip")


def update_latest_commit(path: str):
    commit_hash = get_latest_commit(10)

    with open(path, 'r+') as update_check_py:
        update_check_py_read = update_check_py.read()
        assert '{THIS_COMMIT}'.replace('_', '') in update_check_py_read
        update_check_py.seek(0)
        update_check_py.write(update_check_py_read.replace('{THISCOMMIT}', commit_hash))

    print(f"Wrote {commit_hash} to {os.path.abspath(path)}")


def get_latest_commit(timeout: int) -> str:
    commit_request = requests.get('https://api.github.com/repos/Kataiser/radeline/commits?per_page=1', timeout=timeout, params={'accept': 'application/vnd.github.v3+json'})
    return commit_request.json()[0]['sha']


this_commit = '{THISCOMMIT}'


if __name__ == '__main__':
    is_latest_commit()
