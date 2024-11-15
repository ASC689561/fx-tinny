#!/bin/bash
winecfg -v=win10
wineboot -i
/usr/bin/wine64 /root/.wine/drive_c/fx/icmarketssc5setup.exe /auto

