# Radeline
[![buhbaiSG](buhbaiSG.png)](https://www.frankerfacez.com/emoticon/316755-buhbaiSG)

Chaos monkey that optimizes the [Celeste TAS](https://github.com/ShootMe/CelesteTAS) by randomly changing inputs. Progress is [here](https://github.com/Kataiser/radeline/projects/1) and results go [here](https://github.com/Kataiser/CelesteTAS/tree/radeline-results).

## Instructions
1. Make sure the inputs in Celeste.tas have a breakpoint on the very last line, a chapter restart at the beginning, and end on the chapter complete screen
2. Make sure the most recently run command in Celeste is the correct chapter load (ex. `load 4` or `rmx2 7`)
3. Change `KeyStart` in `Saves\modsettings-CelesteTAS.celeste` to `- OemMinus`, because I couldn't get the default to work
4. Take a look at `settings.yaml` and make sure it's set up correctly
5. Run Celeste Studio, don't edit anything with it though because it doesn't read Radeline's changes to Celeste.tas
5. Install Python >= 3.6 (with pip) and run `run.bat`
