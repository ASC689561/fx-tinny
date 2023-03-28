FROM msjpq/wine-vnc:bionic
RUN apt-get update && apt-get install -y supervisor git && rm -rf /var/lib/apt/lists/*

COPY ./mt5/supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# COPY ./mt5/py /root/.wine/drive_c/py

RUN mkdir -p /config/.wine && WINEPREFIX=/config/.wine winecfg

WORKDIR /root/.wine/drive_c/py/

RUN apt-get update && apt-get install -y wget software-properties-common xvfb 
RUN WINEPREFIX=/config/.wine xvfb-run wine /root/.wine/drive_c/py/icmarketssc5setup.exe /auto || true
RUN WINEPREFIX=/config/.wine wine /root/.wine/drive_c/py/python.exe -m pip install redis pandas


CMD ["/usr/bin/supervisord"]