# Radeline
[![buhbaiSG](buhbaiSG.png)](https://www.frankerfacez.com/emoticon/316755-buhbaiSG)

Chaos monkey that optimizes the [Celeste TAS](https://github.com/ShootMe/CelesteTAS) by randomly changing inputs. Progress is [here](https://github.com/Kataiser/radeline/projects/1) and results go [here](https://github.com/Kataiser/CelesteTAS/tree/radeline-results).

## Instructions
1. Make sure the inputs in Celeste.tas have a breakpoint on the very last line, a chapter restart at the beginning, and end on the chapter complete screen
2. Make sure the most recently run command in Celeste is the correct chapter load (ex. `load 4` or `rmx2 7`)
3. Change `KeyStart` in `Saves\modsettings-CelesteTAS.celeste` to `- P`, because I couldn't get the default to work
4. Time how long the fast-forwarded chapter lasts when it fails on the first input, add like a second for safety, and edit `settings.json.txt` accordingly (and any other changes there if need be)
5. Install Python (with pip) and run `run.bat`
