import subprocess


def main():
    try:
        import keyboard
        import lxml
        import psutil
        import requests
        import win32gui
        import yaml
        from bs4 import BeautifulSoup
    except ModuleNotFoundError:
        subprocess.run('pip install -r requirements.txt')
        print('\n')


if __name__ == '__main__':
    main()
