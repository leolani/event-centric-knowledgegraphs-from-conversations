from datetime import date, timedelta
import random
import json
from json import JSONEncoder
import pickle
from llm_event_triples_openai import LLM_EventExtraction

def convert(datetime_object):
    format = '%Y,%b,%d'
    date_string = datetime_object.strftime(format)
    return date_string

def random_dates(date1, date2, K):
    # getting days between dates
    dates_between = date2 - date1
    total_days = dates_between.days
    res = []
    for idx in range(K):
        random.seed(a=None)
        # getting random days
        random_day = random.randrange(total_days)
        # getting random dates
        res.append(convert(date1 + timedelta(days=random_day)))
    return res

def get_number_of_conversations(input_data):
    cnt = 0
    for utterance in input_data:
        if not (utterance.startswith("A: ") or utterance.startswith("P=") or utterance.startswith("P: ")):
            cnt +=1
    return cnt+10 ## add one for the final chat

def read_conversations_diabetes(path_to_data):
    conversations = []
    f = open(path_to_data)
    print(path_to_data)
    input_data = f.readlines()
    conversation = []
    turns = []
    human = "human"
    date1, date2 = date(2010, 2, 3), date(2015, 7, 1)
    nr_of_conversations = get_number_of_conversations(input_data)
    dates = random_dates(date1, date2, nr_of_conversations)
    conv_cnt = 0
    turn_cnt = 0
    for utterance in input_data:
        if utterance.startswith("P="):
            human = utterance[2:].replace('\n','')
        elif not (utterance.startswith("A: ") or utterance.startswith("P: ")):
            conversation = {'chat': conv_cnt, 'human': human, 'date':str(dates[conv_cnt]), 'turns': turns}
            conversations.append(conversation)
            conv_cnt +=1
            turns = []
            turn_cnt = 0
        else:
            turn_cnt +=1
            speaker = human
            if utterance.startswith("A: "):
                speaker = "agent"
            turn = {'turn': turn_cnt, "speaker": speaker, "utterance": utterance[3:].replace('\n','')}
            turns.append(turn)
    ### Adding the last one
    conv_cnt +=1
    conversation = {'chat': conv_cnt, 'human': human, 'date':dates[conv_cnt], 'turns': turns}
    conversations.append(conversation)
    f.close()
    print("Nr. of conversations", len(conversations))
    return conversations


def main():
    filepath = "../../data/conversations.json"
    f = open(filepath, "r")
    conversations = json.load(f)

    all_annotations = []
    llm_extractor = LLM_EventExtraction()
    for conversation in conversations:
        ### Only human turns are annotated
        #annotations = llm_extractor.annotate_speaker1_conversation(conversation)
        ### Both human turns and agent turns are annotated
        annotations = llm_extractor.annotate_all_turns_in_conversation(conversation)
        all_annotations.append(annotations)

    # subclass JSONEncoder
    class EventEncoder(JSONEncoder):
        def default(self, o):
            return o.__dict__

    f = open("../../data/event_srl.json", "w")
    json.dump(all_annotations, f, indent=4, cls=EventEncoder)


if __name__ == "__main__":
    main()
