import pandas as pd
import numpy as np
from datetime import datetime
from firebase.firebase import get_config, add_document, upload_file, read_collection, read_document, delete_document, read_document_with_filter
from pytz import timezone
import os
from pytz import timezone
import sys
import yaml
import pyrebase
from pathlib import Path
import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore
from datetime import datetime
from pytz import timezone
from typing import List, Dict
from google.cloud.firestore_v1.base_query import FieldFilter, Or, And
from google.cloud.firestore_v1.base_query import BaseCompositeFilter
import random

def upcoming(farmer_tg_id: int):
    '''
    Load calendar with upcoming events. begin time > current time
    
    Args:
        farmer_tg_id: int
            farmer telegram id
    '''
    firebase_config = get_config()
    tz = timezone(firebase_config['timezone'])
    time = datetime.now(tz=tz)
    try:
        app = firebase_admin.get_app()
    except ValueError as e:
        cred = credentials.Certificate(firebase_config["serviceAccount"])
        firebase_admin.initialize_app(cred)
    db = firestore.client()
    docs = db.collection("calendar_events").where(filter=FieldFilter(
            "farmer_tg_id",
            "==",
            farmer_tg_id
        )).where(filter=FieldFilter(
            "timestamp_begin",
            ">",
            time
        )).order_by("timestamp_begin").order_by("timestamp_end").get()
    collection_data = []
    if len(docs) == 0:
        print('Collection not found: {}'.format("calendar_events"))
    for doc in docs:
        collection_data.append(
            {
                "document_id": doc.id,
                "data": doc.to_dict()
            }
        )
    return collection_data
    
def outstanding(farmer_tg_id: int):
    '''
    Load calendar with outstanding events. begin time <= current time <= end time. status is "creation", "notified_farmer", "refused"
    
    Args:
        farmer_tg_id: int
            farmer telegram id
    '''
    firebase_config = get_config()
    tz = timezone(firebase_config['timezone'])
    time = datetime.now(tz=tz)
    try:
        app = firebase_admin.get_app()
    except ValueError as e:
        cred = credentials.Certificate(firebase_config["serviceAccount"])
        firebase_admin.initialize_app(cred)
    db = firestore.client()
    docs = db.collection("calendar_events").where(filter=FieldFilter(
            "farmer_tg_id",
            "==",
            farmer_tg_id
        )).where(filter=FieldFilter(
            "timestamp_end",
            ">=",
            time
        )).where(filter=FieldFilter(
            "status",
            "in",
            ["creation", "notified_farmer", "refused"]
        )).order_by("timestamp_end").get()
    collection_data = []
    if len(docs) == 0:
        print('Collection not found: {}'.format("calendar_events"))
    for doc in docs:
        data = doc.to_dict()
        if data["timestamp_begin"] <= time:
            collection_data.append(
                {
                    "document_id": doc.id,
                    "data": data
                }
            )
    return collection_data
    
def pending(farmer_tg_id: int):
    '''
    Load calendar with pending events. satus is "farmer_response", "notified_agronomist"
    
    Args:
        farmer_tg_id: int
            farmer telegram id
    '''
    firebase_config = get_config()
    tz = timezone(firebase_config['timezone'])
    time = datetime.now(tz=tz)
    try:
        app = firebase_admin.get_app()
    except ValueError as e:
        cred = credentials.Certificate(firebase_config["serviceAccount"])
        firebase_admin.initialize_app(cred)
    db = firestore.client()

    docs = db.collection("calendar_events").where(filter=FieldFilter(
        "farmer_tg_id",
        "==",
        farmer_tg_id
    )).where(filter=FieldFilter(
        "status",
        "in",
        ["farmer_response", "notified_agronomist"]
    )).order_by("timestamp_end", direction=firestore.Query.DESCENDING).get()
   

    '''
    past
    docs = db.collection("calendar_events").where(filter=FieldFilter(
            "farmer_tg_id",
            "==",
            farmer_tg_id
        )).where(filter=BaseCompositeFilter(
            "OR",
            [
                BaseCompositeFilter(
                "AND",
                [
                    FieldFilter("timestamp_end",
                    "<",
                        time
                    ), FieldFilter(
                        "status",
                        "in",
                        ["farmer_response", "notified_agronomist", "accepted", "completed"]
                    )
                ]
                )
                , FieldFilter(
                    "status",
                    "in",
                    ["accepted", "completed"]
                )
        ]
    )).order_by("timestamp_end", direction=firestore.Query.DESCENDING).get()
    '''
    collection_data = []
    if len(docs) == 0:
        print('Collection not found: {}'.format("calendar_events"))
    for doc in docs:
        collection_data.append(
            {
                "document_id": doc.id,
                "data": doc.to_dict()
            }
        )
    return collection_data
    
def overdue(farmer_tg_id: int):
    '''
    Load calendar with overdue events. end time <= current time and status is "notified_farmer" or "refused"
    
    Args:
        farmer_tg_id: int
            farmer telegram id
    '''
    firebase_config = get_config()
    tz = timezone(firebase_config['timezone'])
    time = datetime.now(tz=tz)
    try:
        app = firebase_admin.get_app()
    except ValueError as e:
        cred = credentials.Certificate(firebase_config["serviceAccount"])
        firebase_admin.initialize_app(cred)
    db = firestore.client()
    docs = db.collection("calendar_events").where(filter=FieldFilter(
            "farmer_tg_id",
            "==",
            farmer_tg_id
        )).where(filter=FieldFilter(
            "timestamp_end",
            "<",
            time
        )).where(filter=FieldFilter(
            "status",
            "in",
            ["notified_farmer", "refused"]
        )).order_by("timestamp_end").get()
    collection_data = []
    if len(docs) == 0:
        print('Collection not found: {}'.format("calendar_events"))
    for doc in docs:
        collection_data.append(
            {
                "document_id": doc.id,
                "data": doc.to_dict()
            }
        )
    return collection_data
    
def download_information(farmer_tg_id: int, name_calendar: str):
    df = pd.DataFrame()
    print(farmer_tg_id, name_calendar)
    if name_calendar == "Upcoming":
        info = upcoming(farmer_tg_id)
    if name_calendar == "Outstanding":
        info = outstanding(farmer_tg_id)
    if name_calendar == "Pending":
        info = pending(farmer_tg_id)
    if name_calendar == "Overdue":
        info = overdue(farmer_tg_id)
        
    if name_calendar == "problems_for_support":
        info = read_document_with_filter('user_telegram_id', '==', farmer_tg_id, name_calendar)
    print(info)
    doc = {'document_id': []}
    for i in info:
        doc['document_id'].append(i['document_id'])
        for j in i['data'].keys():
            if j in doc.keys():
                doc[j].append(i['data'][j])
            else:
                doc[j] = [i['data'][j]]
    for key in doc.keys():
        df[key] = doc[key]
    return df

def to_DataFrame_information(info):
    df = pd.DataFrame()
    doc = {'document_id': []}
    for i in info:
        doc['document_id'].append(i['document_id'])
        for j in i['data'].keys():
            if j in doc.keys():
                doc[j].append(i['data'][j])
            else:
                doc[j] = [i['data'][j]]
    for key in doc.keys():
        df[key] = doc[key]
    return df
