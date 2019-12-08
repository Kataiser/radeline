import subprocess


def main():
    try:
        import keyboard
        import lxml
        import psutil
        import yaml
        from bs4 import BeautifulSoup
    except ModuleNotFoundError:
        subprocess.run('pip install -r requirements.txt')


if __name__ == '__main__':
    main()
