import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from firebase.firebase import (add_document, read_collection, 
                      read_document, delete_document, read_document_with_filter, update_document,
                      read_collection_with_composite_filter, read_collection_with_composite_filter)


def download_problems_for_support(collection, problem, id, person):
    df = pd.DataFrame()
    info = read_collection_with_composite_filter(
        collection,
        [{'atribut': 'problem', 'op': '==', 'value': problem},
        {'atribut': 'user_telegram_id', 'op': '==', 'value': id}]
    )
    if not info:
        print('bububu')
        return df
    
    doc = {'document_id': [], 'person': []}
    for i in info:
        doc['document_id'].append(i['document_id'])
        doc['person'].append(person)
        for j in i['data'].keys():
            if j in doc.keys():
                doc[j].append(i['data'][j])
            else:
                doc[j] = [i['data'][j]]
    print(info)
    print(doc)
    print(df)
    for key in doc.keys():
        df[key] = doc[key]
    return df


def download_information(collection: str, op=None):
    df = pd.DataFrame()
    if op is None:
        info = read_collection(collection)
    else:
        info = read_document_with_filter('user_telegram_id', '==', op, collection)
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
    if 'timestamp_end' in doc.keys():
        df = df.sort_values(by='timestamp_end', ascending=False)
    if 'time' in doc.keys():
        df = df.sort_values(by='time')
    return df

def add_information(collection, document, df):
    document['document_id'] = add_document(document, collection)
    document = pd.DataFrame(document, index=[0])
    df = pd.concat([df, document], ignore_index=True)
    return df

def merge_and_sortes_message_about_problems(problem, id):
    
    df1 = download_problems_for_support('telegram_message_from_support_for_farmer', problem, id, 'agronomist')
    df2 = download_problems_for_support('telegram_message_from_farmer_for_support', problem, id, 'farmer')
    if df1.empty and not df2.empty:
         merged_df = df2
    elif df2.empty and not df1.empty:
        merged_df = df1
    if df1.empty and df2.empty:
        return pd.DataFrame()
    else:
        merged_df = pd.concat([df1, df2])
    merged_df = merged_df.reset_index(drop=True)
    sorted_df = merged_df.sort_values(by='time')
    return sorted_df

'''
def download_unread_message_for_support(id):
    df = to_DataFrame_information(read_collection_with_composite_filter(
        'telegram_message_from_farmer_for_support',
        [{'atribut': 'status', 'op': '==', 'value': 'unread'},
         {'atribut': 'user_telegram_id', 'op': '==', 'value': id}]))
    return df
'''
