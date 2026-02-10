import sys, getopt
import pandas as pd
import pathlib
import json
import os
from pathlib import Path
from collections import Counter
from nltk.tokenize import sent_tokenize


def read_conversations_harry(path_to_data):
    conversations = []
    for path in list(path_to_data.rglob('*.json')):
        f = open(path)
        print(path)
        data = json.load(f)
        for j in data:
            conversations.append(data[j]["dialogue"])
            for conversation in conversations:
                clean_conversation = []
                for turn in conversation:
                    utterance = turn[turn.find(':') + 2:]
                    clean_conversation.append(utterance)
                conversation = clean_conversation
        f.close()
    print("Nr. of conversations", len(conversations))
    return conversations


def read_conversations_opendialog(path_to_data):
    conversations = []
    df = pd.read_csv(path_to_data)
    for item in df["Messages"]:
        conversation = json.loads(item)
        clean_conversation = []
        for data in conversation:
            utterance = None
            if 'message' in data:
                utterance = data['message']
            elif 'metadata' in data:
                metadata = data['metadata']
                if 'text' in metadata:
                    utterance = metadata['text']
            if utterance:
                clean_conversation.append(utterance)
        conversations.append(clean_conversation)
    print("Nr. of conversations", len(conversations))
    return conversations


def read_conversations_dialogre(path_to_data):
    conversations = []
    for path in list(path_to_data.rglob('*.json')):
        f = open(path)
        print(path)
        data = json.load(f)
        for j in data:
            conversation = j[0]
            clean_conversation = []
            for turn in conversation:
                utterance = turn[turn.find(':') + 2:]
                clean_conversation.append(utterance)
            conversations.append(clean_conversation)
        f.close()
    print("Nr. of conversations", len(conversations))
    return conversations


def read_conversations_pedc(path_to_data):
    conversations = []
    for path in list(path_to_data.rglob('*.txt')):
        f = open(path)
        print(path)
        input_data = f.readlines()
        conversation = []
        for utterance in input_data:
            utterance = utterance.replace("\t", " ")
            conversation.append(utterance)
        conversations.append(conversation)
        f.close()
    print("Nr. of conversations", len(conversations))
    return conversations

def read_conversations_diabetes(path_to_data):
    conversations = []
    f = open(path_to_data)
    print(path_to_data)
    input_data = f.readlines()
    conversation = []
    for utterance in input_data:
        if not (utterance.startswith("A: ") or utterance.startswith("P: ")):
            conversations.append(conversation)
            conversation = []
        else:
            conversation.append(utterance[3:])
    conversations.append(conversation)
    f.close()
    print("Nr. of conversations", len(conversations))
    return conversations

def read_conversations_multiwoz(path_to_data):
    conversations = []
    for path in list(path_to_data.rglob('dialogues_*.json')):
        f = open(path)
        print(path)
        data = json.load(f)
        for j in data:
            turns = j["turns"]
            conversation = []
            for turn in turns:
                conversation.append(turn["utterance"])
            conversations.append(conversation)
        f.close()
    return conversations
