#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script name: Weather.py
Author: Nick
Date: July 2018
Purpose: Used to fetch and process weather data from ncas' Leeds Weather Data archive
"""

import matplotlib
matplotlib.use('Agg')
import os
import sys
import ssl
import pandas as pd
import datetime
import math
import cmath
import datetime as dt
import numpy as np
import matplotlib.pyplot as plt
import matplotlib as mpl

def fetchWeatherData(date):
    if (not os.environ.get('PYTHONHTTPSVERIFY', '') and
            getattr(ssl, '_create_unverified_context', None)):
        ssl._create_default_https_context = ssl._create_unverified_context

        yearstring = str(date.year)
        monthstring = str(date.month) if date.month >= 10 else "0"+str(date.month)
        daystring = str(date.day) if date.day >= 10 else "0"+str(date.day)

        datestring = yearstring + "-" + monthstring + "-" + daystring
        url = "https://sci.ncas.ac.uk/leedsweather/Archive/CUSTOM-ARC-"+datestring+"-METRIC.csv"
        weatherdata = pd.read_csv(url, parse_dates=[0], index_col=[0])
        ambientData = weatherdata[['Temp / °C','Humid%','Pressure / hPa']]
        ambientData = ambientData.resample('H').mean()
        ambientData = ambientData.iloc[[date.hour]]
        ambientData = ambientData.round(1)

        windData = weatherdata[['Wind / ms¯¹','Winddir / °']]
        startTime = date.strftime("%H:%M:%S")

        timeplushour = date + datetime.timedelta(0,3600)
        endTime = timeplushour.strftime("%H:%M:%S")
        windData = windData.between_time(startTime, endTime)
        arrSpeed = windData['Wind / ms¯¹'].tolist()
        arrDirection = windData['Winddir / °'].tolist()

        wDirection, wSpeed = polarAverage(arrDirection, arrSpeed)

        print(ambientData)

        viewModel = {
            'Temp / °C': ambientData.values[0][0]
            ,'Humid%': ambientData.values[0][1]
            ,'Pressure / hPa': ambientData.values[0][2]
            ,'Wind / ms¯¹': wSpeed
            ,'Winddir / °': wDirection
        }

        return viewModel

# http://www.intellovations.com/2011/01/16/wind-observation-calculations-in-fortran-and-python/
def polarAverage(arrDirection, arrSpeed):
    wind_vector_sum = None

    for i in range(0, arrDirection.__len__()-1):
        direction = math.radians(arrDirection[i])
        wind_polar = cmath.rect(arrSpeed[i], direction)
        if wind_vector_sum is None:
            wind_vector_sum = wind_polar
        else:
            wind_vector_sum += wind_polar

    r, phi = cmath.polar(wind_vector_sum / arrDirection.__len__())

    rwdir = math.degrees(phi) % 360
    rwspd = r
    # rwdir = int(round(int(round(math.degrees(phi) % 360)) / 10.0))
    # rwspd = int(round(r * 10)) / 10.0

    return '%2.0f' % rwdir, '%5.1f' % rwspd