import os
import shutil
import site
import subprocess
import sys
import zipfile
from io import BytesIO

import requests

try:
    import requests_cache
except ImportError:
    requests_cache = None


def main():
    print("Building Radeline release package\n")

    backups_path = r'Radeline\Optimizer\Backups'
    if os.path.isdir(backups_path) and os.listdir(backups_path):
        print("Backed up the optimizer backups")
        shutil.copytree(backups_path, 'backups', dirs_exist_ok=True)

    if os.path.isdir('Radeline'):
        print("Deleting old build folder")
        shutil.rmtree('Radeline')
    else:
        print("No old build folder to delete")

    print('Creating new build folder')
    os.mkdir('Radeline')
    os.mkdir('Radeline\\Optimizer')
    os.mkdir('Radeline\\Optimizer\\Backups')
    os.mkdir('Radeline\\Simulator')

    compile_command = f'{sys.executable} "movement sim\\setup.py" build_ext --inplace'
    subprocess.run(compile_command)
    print("Copied", shutil.copy('movement sim\\sim_compiled.cp310-win32.pyd', 'Radeline\\Simulator\\'))

    if requests_cache:
        print("Using DL cache for interpreter")
        requests_cache.install_cache('interpreter_dl_cache')
    else:
        print("Not using DL cache for interpreter")

    interpreter_url = 'https://www.python.org/ftp/python/3.10.1/python-3.10.1-embed-win32.zip'
    print(f"Downloading Python interpreter from {interpreter_url}...")
    interpreter_data = requests.get(interpreter_url, timeout=30).content
    with zipfile.ZipFile(BytesIO(interpreter_data), 'r') as interpreter_zip:
        interpreter_zip.extractall(path=f"Radeline\\{interpreter_url.split('/')[-1][:-4]}\\")

    packages_dir = site.getsitepackages()[1]
    needed_packages = ['beautifulsoup4', 'bs4', 'certifi', 'charset_normalizer', 'idna', 'keyboard', 'lxml', 'psutil', 'pyperclip', 'requests', 'soupsieve', 'tqdm', 'urllib3', 'yaml']
    for site_package in os.listdir(packages_dir):
        for needed_package in needed_packages:
            if needed_package in site_package and os.path.isdir(f'{packages_dir}\\{site_package}'):
                shutil.copytree(f'{packages_dir}\\{site_package}', f'Radeline\\packages\\{site_package}')
                break
    print(f"Copied {len(needed_packages)} packages from {packages_dir} to Radeline\\packages")
    shutil.rmtree('Radeline\\packages\\psutil\\tests')
    print("Deleted psutil and bs4 tests")

    print("Copied", shutil.copy('README.md', 'Radeline'))
    print("Copied", shutil.copy('LICENSE', 'Radeline'))
    print("Copied", shutil.copy('optimizer\\main.py', 'Radeline\\Optimizer'))
    print("Copied", shutil.copy('optimizer\\run.py', 'Radeline\\Optimizer'))
    print("Copied", shutil.copy('optimizer\\run.bat', 'Radeline\\Optimizer'))
    print("Copied", shutil.copy('optimizer\\settings.yaml', 'Radeline\\Optimizer'))
    print("Copied", shutil.copy('movement sim\\run.py', 'Radeline\\Simulator'))
    print("Copied", shutil.copy('movement sim\\run.bat', 'Radeline\\Simulator'))
    print("Copied", shutil.copy('movement sim\\config.yaml', 'Radeline\\Simulator'))
    print("Copied", shutil.copy('movement sim\\input_formatter.py', 'Radeline\\Simulator'))
    print("Copied", shutil.copy('movement sim\\run_formatter.py', 'Radeline\\Simulator'))
    print("Copied", shutil.copy('movement sim\\run formatter.bat', 'Radeline\\Simulator'))

    print("\nBuild finished")


if __name__ == '__main__':
    main()
