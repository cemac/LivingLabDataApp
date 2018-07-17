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
        hourlydata = weatherdata.resample('H').mean()

        return hourlydata
