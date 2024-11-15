#!/bin/bash
wget https://www.python.org/ftp/python/3.11.1/python-3.11.1-amd64.exe
wget https://bootstrap.pypa.io/get-pip.py


winecfg -v=win10
wine python-3.11.1-amd64.exe AssociateFiles=0 Shortcuts=0 Include_doc=0 Include_dev=0 Include_launcher=0 InstallLauncherAllUsers=0 Include_tcltk=0 Include_test=0 InstallAllUsers=0 DefaultJustForMeTargetDir="/root/.wine/drive_c/python/" SimpleInstall=0 /quiet
wine python/python.exe get-pip.py
wine python/python.exe -m pip install  numpy==1.26.4 MetaTrader5 pandas==2.2.2 fastapi[all]==0.111.0 kazoo==2.10.0 pydantic-core==2.18.2

