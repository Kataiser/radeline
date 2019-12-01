# Radeline
[![buhbaiSG](buhbaiSG.png)](https://www.frankerfacez.com/emoticon/316755-buhbaiSG)

Chaos monkey that improves the [Celeste TAS](https://github.com/ShootMe/CelesteTAS) by randomly changing inputs. Its results go [here](https://github.com/Kataiser/CelesteTAS/tree/radeline-results).

## Instructions
1. Make sure the data in Celeste.tas has a breakpoint on the very last line and a chapter restart at the beginning
2. Make sure the most recently run command in Celeste is the correct chapter load (ex. `load 4` or `rmx2 7`)
3. Change `KeyStart` in `Saves\modsettings-CelesteTAS.celeste` to `- P`, because I couldn't get the default to work
4. Time how long the fast-forwarded chapter lasts when it fails on the first input, add like a second, and edit `settings.json.txt` accordingly (and any other changes there if need be)
5. Install Python (with pip) and run `run.bat`
