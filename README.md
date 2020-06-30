# Radeline
[![buhbaiSG](buhbaiSG.png)](https://www.frankerfacez.com/emoticon/316755-buhbaiSG)

Chaos monkey that optimizes the [Celeste TAS](https://github.com/ShootMe/CelesteTAS) by randomly (or sequentially) changing inputs. Progress for the main game is [here](https://github.com/Kataiser/radeline/projects/1) and results go [here](https://github.com/Kataiser/CelesteTAS/tree/radeline-results) (but I've stopped working on it).

## Instructions
1. Change `KeyStart` in `Saves\modsettings-CelesteTAS.celeste` to `- OemMinus`, because I couldn't get the default bind to work
2. Make sure the inputs in Celeste.tas have a breakpoint on the very last line, a chapter restart at the beginning, and end on the chapter complete screen (or a S&Q)
3. If you're not using the `console load` start method, make sure the most recently run command in Celeste is the correct chapter load (ex. `load 4` or `rmx2 7`)
4. Take a look at `settings.yaml` (it's just a text file) and make sure it's configured correctly
5. Be careful with Celeste Studio because it doesn't read Radeline's changes to Celeste.tas and so you could easily accidentally overwrite it
6. Install Python >= 3.6 (with pip and "Add python to environment variables" checked)
7. (Optional) Install [Cython](https://pypi.org/project/Cython/) and run `build.bat`
8. Run `run.bat`

If you need any assistance, DM me on Discord at Kataiser#4640

## Why the name?
Because it's a little dumb and almost insulting to real TASers, but dangit if it isn't really cool sometimes (also, Random Madeline). I kind of regret the name and just call it "my optimization script" half the time though
