#!/bin/bash

export DISPLAY=:0
export XAUTHORITY=/home/ian/.Xauthority
export XDG_RUNTIME_DIR=/run/user/1000

python meteogram.py
pcmanfm --desktop
pcmanfm -w output.png
