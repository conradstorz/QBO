#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Standardize time strings and datetime objects used in a project.
"""


from datetime import datetime, date
from time import sleep
import pytz


tz_UTC = pytz.timezone("UTC")
tz_LOCAL = pytz.timezone("America/Louisville")


def timefstring(dtobj):
    """Standardize the format used for timestamp string format.
    """
    return f'{dtobj.strftime("%Y-%m-%d_%H:%M:%S")}'

def LOCAL_TODAY():
    return  date.today()

def UTC_NOW():
    return datetime.now(tz_UTC)

def LOCAL_CURRENT_YEAR():
    return str(LOCAL_TODAY().year)

def LOCAL_TODAY_STRING():
    return LOCAL_TODAY().strftime("%Y-%m-%d")

def UTC_NOW_STRING():
    return "".join([timefstring(UTC_NOW()), 'UTC'])

def LOCAL_NOW():
    return datetime.now(tz_LOCAL)

def LOCAL_NOW_STRING():
    return "".join([timefstring(LOCAL_NOW()), 'EST'])


if __name__ == "__main__":
    for i in range(5):
        print(f"LOCAL TODAY: {LOCAL_TODAY()} type: {type(LOCAL_TODAY())}")
        print(f"UTC NOW: {UTC_NOW()} type: {type(UTC_NOW())}")
        print(f"LOCAL NOW: {LOCAL_NOW()} type: {type(LOCAL_NOW())}")
        print(f"LOCAL CURRENT_YEAR: {LOCAL_CURRENT_YEAR()} type: {type(LOCAL_CURRENT_YEAR())}")
        print(f"LOCAL TODAY_STRING: {LOCAL_TODAY_STRING()} type: {type(LOCAL_TODAY_STRING())}")
        print(f"UTC NOW_STRING: {UTC_NOW_STRING()} type: {type(UTC_NOW_STRING())}")
        print(f"LOCAL NOW_STRING: {LOCAL_NOW_STRING()} type: {type(LOCAL_NOW_STRING())}")
        sleep(2)
        print()

