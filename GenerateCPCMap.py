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
import gmplot
import numpy as np
import argparse
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
        if "Time,Concentration" in l:
            iHeader=i
    assert iStartDate >= 0, "Start date not found in CPC file header"
    assert iStartTime >= 0, "Start time not found in CPC file header"
    assert iSampleLen >= 0, "Sample length not found in CPC file header"
    assert iHeader >= 0, "CPC file data header must contain Time and Concentration fields"
    #Start Date:
    temp=lines[iStartDate].split(',')
    splt=[ int(x) for x in temp[1].split('/')]
    startDate=dt.date(splt[2]+2000,splt[0],splt[1])
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
        if(temp[0]==''):
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
            if abs((CPCdate-startDate).total_seconds()) < 300:
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
    assert abs((endDateCPC-endDate).total_seconds()) < 300, "No valid GPS activities with an end time within 5 minutes of the CPC data file end time"
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


def CreateMap(MergeData,id,MAP_DIR,addMarkers=True):
    #conc data limits/colours:
    binLims=[1000,2000,3000,4000,5000,7500,10000,15000,20000]
    colsHex=['#00FF40','#00FF00','#40FF00','#80FF00','#BFFF00','#FFFF00','#FFBF00','#FF8000','#FF0000','#8000FF']
    #Plot using gmplot:
    lonMin=min(MergeData['lon'])
    lonMax=max(MergeData['lon'])
    latMin=min(MergeData['lat'])
    latMax=max(MergeData['lat'])
    lats=MergeData['lat'].values
    lons=MergeData['lon'].values
    concs=MergeData['conc'].values
    gmap = gmplot.GoogleMapPlotter(np.mean([latMin,latMax]),np.mean([lonMin,lonMax]),zoom=16,apikey='AIzaSyCxHEzf7TNaVsha6owD_DgbZwzX16_cCcE')
    circSize=7
    for i in np.arange(0,len(lats)):
        if concs[i] <= binLims[0]:
            gmap.circle(lats[i],lons[i],radius=circSize,color=colsHex[0])
        for j in np.arange(0,len(binLims)-1):
            if concs[i] > binLims[j] and concs[i] <= binLims[j+1]:
                gmap.circle(lats[i],lons[i],radius=circSize,color=colsHex[j+1])
        if concs[i] > binLims[-1]:
            gmap.circle(lats[i],lons[i],radius=circSize,color=colsHex[-1])
    #Add start and end markers
    if addMarkers:
        gmap.marker(lats[0],lons[0],title="START",color="#008000")
        gmap.marker(lats[-1],lons[-1],title="FINISH",color="#FF0000")
        #Add N more markers at regular intervals
        N=10
        for i in np.arange(1,N+1):
            j=int(len(lats)*(i/(N+1)))
            gmap.marker(lats[j],lons[j],title=i,color="#D3D3D3")
    #Write to file
    HTMLfile = 'map_'+id+'.html'
    gmap.draw(MAP_DIR+'/'+HTMLfile)
    #Output color bar:
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
    plt.savefig("static/colourbar.png", dpi=300, transparent=True)
    return HTMLfile

def BuildMap(MAP_DIR,id,mapFileIn,mapTitle):
    #find/replace strings
    find = [
    '<title>Google Maps - pygmaps </title>',
    'ROADMAP',
    'padding:0px',
    '<div id="map_canvas" style="width: 100%; height: 100%;"></div>']
    replace = [
    '<title>Map</title>\n\
<style>\n\
.center-div\n\
{\n\
  margin: 0 auto;\n\
  width: 100px;\n\
}\n\
</style>',
    'SATELLITE',
    'padding:30px',
    '<h1 style="text-align:center;">'+mapTitle+'</h1>\n\
  <p style="text-align:center;"><img src="/static/colourbar.png" alt="colour bar" style="width:750px;"></p>\n\
  <div id="map_canvas" style="width: 1000px; height: 600px;" class="center-div"></div>']
    #open two files (one to read one to write)
    inFile = open(MAP_DIR+'/'+mapFileIn,'r')
    mapFileOut = 'map_'+id+'_mod.html'
    outFile = open(MAP_DIR+'/'+mapFileOut,'w')
    #Loop over lines in input file
    for line in inFile:
        #find/replace strings:
        for i in np.arange(0,len(find)):
            if find[i] in line:
                line = line.replace(find[i],replace[i])
        #contains/replace strings
        if 'MarkerImage' in line:
            splt=line.split('/')
            hexCode=splt[-1][0:6]
            line="    var img = new google.maps.MarkerImage('/static/"+hexCode+".png');\n"
        #write line to output file
        outFile.write(line)
    #close the files
    inFile.close()
    outFile.close()
    return mapFileOut
