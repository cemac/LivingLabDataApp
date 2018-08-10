#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""

Script name: SpatialAnalysis.py
Author: NICK
Date: June 2018
Purpose: Used to carryout spatial analysis on data using Shapely

"""

from shapely.geometry import shape
from shapely.geometry import Point
from shapely.geometry import geo
import json
from rtree import index


def ReadGeoJSON(path):
    with open(path) as hexFile:
        data = json.load(hexFile)
        cells = []
        for feature in data['features']:
            cells.append(shape(feature['geometry']))
        return cells


def SpatialJoin(points, polygons):
    idx = index.Index()
    count = -1

    for poly in polygons:
        count += 1
        idx.insert(count, poly.polygon.bounds)

    for i, conc in enumerate(points.concs):
        for j in idx.intersection((points.lons[i], points.lats[i])):
            if Point(points.lons[i], points.lats[i]).within(polygons[j].polygon):
                polygons[j].concs.append(conc)
                break

    return polygons

