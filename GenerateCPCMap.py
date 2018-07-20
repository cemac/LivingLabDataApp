#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script name: GenerateCPCMap.py
Author: JON
Date: January 2018
Purpose: Used to generate an interactive google map showing concentration data
         collected by volunteers carrying a CPC (condensation particle counter)
         around Leeds University campus.
"""

import matplotlib
matplotlib.use('Agg')
import os
import sys
import pandas as pd
import datetime as dt
import numpy as np
import matplotlib.pyplot as plt
import matplotlib as mpl
from stravalib.client import Client

def ReadCPCFile(CPCtext):
    lines=CPCtext.splitlines()
    ##Read in required metadata:
    iStartDate=-999
    iStartTime=-999
    iSampleLen=-999
    iHeader=-999
    for i,l in enumerate(lines[0:20]):
        if l[0:10] == "Start Date":
            iStartDate=i
        if l[0:10] == "Start Time":
            iStartTime=i
        if l[0:13] == "Sample Length":
            iSampleLen=i
        if "Time" in l and "Concentration" in l:
            iHeader=i
    assert iStartDate >= 0, "Start date not found in CPC file header"
    assert iStartTime >= 0, "Start time not found in CPC file header"
    assert iSampleLen >= 0, "Sample length not found in CPC file header"
    assert iHeader >= 0, "CPC file data header must contain Time and Concentration fields"
    #Start Date:
    temp=lines[iStartDate].split(',')
    splt=[int(x) for x in temp[1].split('/')]
    #Year might be in YY or YYYY format:
    if splt[2]>2000:
        startYear=splt[2]
    else:
        startYear=splt[2]+2000
    startDate=dt.date(startYear,splt[0],splt[1])
    #Start Time:
    temp=lines[iStartTime].split(',')
    splt=[ int(x) for x in temp[1].split(':')]
    startTime=dt.time(splt[0],splt[1],splt[2])
    #Start Date/Time:
    startDateTime=dt.datetime(startDate.year,startDate.month,startDate.day,startTime.hour,startTime.minute,startTime.second)
    #Sample length:
    temp=lines[iSampleLen].split(',')
    if ':' in temp[1]:
        splt=[ int(x) for x in temp[1].split(':')]
        sampleLen=splt[0]*60 + splt[1]
    else:
        sampleLen=int(temp[1])
    ##Now read in CPC data:
    #start and end lines of data block:
    startLine=iHeader+1
    for i in range(len(lines)-2,len(lines)-10,-1):
        temp=lines[i].split(',')
        if(temp[0]=='' or 'Comment for Sample 1'):
            continue
        else:
            break
    endLine=i
    #Get index of time and conc data columns:
    splt=lines[iHeader].split(',')
    if len(splt)<=2 or splt[2]=='':
        iTime=0
        iConc=1
    elif len(splt)==3:
        iTime=1
        iConc=2
    else:
        sys.exit("Unexpected number of data columns in CPC file")
    #read data in:
    dateTime=[]
    conc=[]
    for l in lines[startLine:endLine]:
        temp=l.split(',')
        splt=[ int(x) for x in temp[iTime].split(':')]
        dateTime.append(dt.datetime(startDate.year,startDate.month,startDate.day,splt[0],splt[1],splt[2]))
        conc.append(int(float(temp[iConc])))
    CPCData=pd.DataFrame(data={'conc':conc,'dateTime':dateTime})
    return CPCData,startDateTime,sampleLen


def FetchGPSData(tokensFile,CPCdate,CPClen):
    client = Client()
    ###To get the saved access tokens below, I did the following:
    ##1. Run the following lines:
    #authorize_url = client.authorization_url(client_id=22380, redirect_uri='http://sustainability.leeds.ac.uk',approval_prompt='force')
    #print(authorize_url)
    ##2. Paste the above url into a browser, accept the request,
    ##   and copy the 'code' from the resulting url into the following line,
    ##   along with the client_secret which can be found under air pollution9 account on strava:
    #access_token = client.exchange_code_for_token(client_id=22380, client_secret='***',
    #  code='***')
    ##3. Extract token from the above variable:
    #print(access_token)
    ###Saved access tokens:
    f=open(tokensFile,'r')
    myTokens=f.read().splitlines()
    f.close()
    #Find activity which most closely matches CPC start date/time and sample length
    #All activities within 5 mins of the CPC start date are considered
    #The activity with the closest-matching elapsed time to the CPC sample length is then chosen
    validActs={}
    for i,token in enumerate(myTokens):
        client.access_token = token
        #athlete = client.get_athlete()
        #print(athlete.firstname,athlete.lastname+':')
        myActivities=client.get_activities()
        for activity in myActivities:
            startDate=activity.start_date_local
            #print('    '+activity.name+':',startDate,'Local time')
            if abs((CPCdate-startDate).total_seconds()) < 60:
                validActs.update({i:activity.id})
    assert len(validActs) > 0, "No GPS activities with a start time within 5 minutes of the CPC data file start time"
    DeltaT=1e10
    for key,value in validActs.items():
        client.access_token=myTokens[key]
        activity=client.get_activity(value)
        elap=activity.elapsed_time.seconds
        thisDT=abs(CPClen-elap)
        if thisDT < DeltaT:
            DeltaT=thisDT
            chosenAth=key
            chosenAct=value
    #Extract required data from chosen activity:
    client.access_token=myTokens[chosenAth]
    activity=client.get_activity(chosenAct)
    startDate=activity.start_date_local
    endDate=startDate+dt.timedelta(seconds=activity.elapsed_time.seconds)
    endDateCPC=CPCdate+dt.timedelta(seconds=CPClen)
    assert abs((endDateCPC-endDate).total_seconds()) < 60, "No valid GPS activities with an end time within 1 minute of the CPC data file end time"
    myTypes = ['time', 'latlng']
    myStream = client.get_activity_streams(chosenAct,types=myTypes)
    latlon=myStream['latlng'].data
    lat=[latlon[i][0] for i in range(len(latlon))]
    lon=[latlon[i][1] for i in range(len(latlon))]
    time=myStream['time'].data
    dateTime=[startDate+dt.timedelta(seconds=i) for i in time]
    GPSData=pd.DataFrame(data={'lon':lon,'lat':lat,'dateTime':dateTime})
    return GPSData


def NearestNghbr(CPCData,GPSData):
    MergeData=pd.merge(CPCData,GPSData,on=['dateTime'])
    assert MergeData.shape[0] > 0, "CPC and GPS times don't overlap"
    MergeData=MergeData.drop('dateTime',axis=1)
    return MergeData


def rgba_to_hex(rgba_color) :
    red = int(rgba_color[0]*255)
    green = int(rgba_color[1]*255)
    blue = int(rgba_color[2]*255)
    return '#{r:02x}{g:02x}{b:02x}'.format(r=red,g=green,b=blue)


def ArrayMiddle(minLatLng, maxLatLng):
    return [np.mean([minLatLng[0], maxLatLng[0]]), np.mean([minLatLng[1], maxLatLng[1]])]


def ArrayStats(lats, lons):
    arrstats = {}
    arrstats['min'] = [min(lats), min(lons)]
    arrstats['max'] = [max(lats), max(lons)]
    arrstats['middle'] = ArrayMiddle(arrstats['min'], arrstats['max'])
    return arrstats

def Median(arr):
    return np.median(arr)

def elementMean(arr):
    return np.mean(arr, axis=0)

def elementMin(arr):
    return np.min(arr, axis=0)

def elementMax(arr):
    return np.max(arr, axis=0)

def CreateBins(file):
    #binLims=[1000,2000,3000,4000,5000,7500,10000,15000,20000]
    binLims = np.loadtxt(file, delimiter=',', dtype='int', encoding='utf-8', skiprows=1)
    return binLims

def AssignColours(binLims, colorProfile):
    # List of Colormaps: https://matplotlib.org/users/colormaps.html
    colsHex = []
    if(colorProfile == "gr"):
        rgmap = {'red': ((0.0, 0.1, 0.1),
                         (0.2, 0.0, 0.0),
                         (0.5, 0.96, 0.96),
                         (0.9, 1.0, 1.0),
                         (1.0, 0.5, 0.5)
                         ),

                  'green': ((0.0, 0.6, 0.6),
                            (0.2, 1.0, 1.0),
                            (0.5, 1.0, 1.0),
                            (0.9, 0.0, 0.0),
                            (1.0, 0.0, 0.0),
                            ),

                  'blue': ((0.0, 0.1, 0.1),
                           (0.2, 0.0, 0.0),
                           (0.5, 0.35, 0.35),
                           (0.9, 0.0, 0.0),
                           (1.0, 1.0, 1.0),
                           )
                  }

        cmap = mpl.colors.LinearSegmentedColormap('RedGreen', rgmap)
    else:
        if(colorProfile == "bg"):
            colorMap = 'viridis'
        elif(colorProfile == "by"):
            colorMap = 'inferno'
        else:
            colorMap = 'viridis'                      # if error, default to colorblind
        cmap = matplotlib.cm.get_cmap(colorMap)

    for i in range(0,len(binLims)+1):               # generate a color for each bin
        colsHex.append(rgba_to_hex(cmap(i*1/(len(binLims)))))

    return colsHex


def CreateColourBar(binLims, colsHex, colorProfile):
    fig = plt.figure(figsize=(8, 1))
    axs = fig.add_axes([0.05, 0.55, 0.9, 0.2])
    cmap = mpl.colors.ListedColormap(colsHex[1:-1])
    cmap.set_under(colsHex[0])
    cmap.set_over(colsHex[-1])
    norm = mpl.colors.BoundaryNorm(binLims, cmap.N)
    cb = mpl.colorbar.ColorbarBase(axs, cmap=cmap,
                                    norm=norm,
                                    boundaries=[0.] + binLims + [100000.],
                                    extend='both',
                                    # Make the length of each extension
                                    # the same as the length of the
                                    # interior colors:
                                    extendfrac='auto',
                                    ticks=binLims,
                                    spacing='uniform',
                                    orientation='horizontal')
    cb.set_label('particles per cubic centimetre')
    plt.savefig("static/colourbar_"+colorProfile+".png", dpi=300, transparent=True)

