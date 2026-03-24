import json
import random
from cltl.commons.discrete import UtteranceType
from datetime import date, datetime
from dateutil import parser

def get_dummy_perspective():
    perspective= {"certainty": 1, "polarity": 1, "sentiment": 0}
    return perspective


def extract_go_emotions(utterance: str) -> list:
    """
    Extract GO emotions from an utterance using keyword matching

    Args:
        utterance: Input text to analyze

    Returns:
        List of detected emotions
    """
    # Define your emotion keywords here
    emotion_keywords = {
        "happy": ["joy", "glad", "excited", "elated"],
        "sad": ["sad", "unhappy", "miserable", "depressed"],
        "angry": ["angry", "mad", "irritated", "furious"],
        "neutral": ["neutral", "calm", "indifferent", "objective"]
    }

    detected_emotions = []

    # Convert utterance to lowercase for case-insensitive matching
    utterance_lower = utterance.lower()

    for emotion, keywords in emotion_keywords.items():
        for keyword in keywords:
            if keyword in utterance_lower:
                detected_emotions.append(emotion)
                break  # Avoid duplicate entries for the same emotion

    return detected_emotions
def get_triples_from_object(event, event_id):
    triples = []
    predicate_objects = []
    if event.activity:
        subject = event.activity
        subject_uri = "http://cltl.nl/leolani/n2mu/"+event.activity.replace(" ", "_")+str(event_id)
        if event.agent:
            if type(event.agent)==str:
                event.agent = [event.agent]
            elif type(event.agent)==tuple:
                event.agent = list(event.agent)
            for agent in event.agent:
                triple = {"subject": {"label": subject, "type": ["activity"], "uri": subject_uri},
                  "predicate": {"label": "agent", "uri": "http://cltl.nl/leolani/n2mu/agent"},
                  "object": {"label":agent, "type": ["agent"], "uri": ""}}
                triples.append(triple) 
        if event.patient:
            if type(event.patient)==str:
                event.patient = [event.patient]
            elif type(event.patient)==tuple:
                event.patient = list(event.patient)
            for patient in event.patient:
                triple = {"subject": {"label": subject, "type": ["activity"], "uri": subject_uri},
                  "predicate": {"label": "patient", "uri": "http://cltl.nl/leolani/n2mu/patient"},
                  "object": {"label": patient, "type": ["agent", "object"], "uri": ""}}
                triples.append(triple) 
        if event.manner:
            if type(event.manner)==str:
                event.manner = [event.manner]
            elif type(event.manner)==tuple:
                event.manner = list(event.manner)
            for manner in event.manner:
                triple = {"subject": {"label": subject, "type": ["activity"], "uri": subject_uri},
                  "predicate": {"label": "manner", "uri": "http://cltl.nl/leolani/n2mu/manner"},
                  "object": {"label": manner, "type": ["property"], "uri": ""}}
                triples.append(triple) 
        if event.instrument:
            if type(event.instrument)==str:
                event.instrument = [event.instrument]
            elif type(event.instrument)==tuple:
                event.instrument = list(event.instrument)
            for instrument in event.instrument:
                triple = {"subject": {"label": subject, "type": ["activity"], "uri": subject_uri},
                  "predicate": {"label": "instrument", "uri": "http://cltl.nl/leolani/n2mu/instrument"},
                  "object": {"label": instrument, "type": ["instrument"], "uri": ""}}
                triples.append(triple) 
        if event.location:
            if type(event.location)==str:
                event.location = [event.location]
            elif type(event.location)==tuple:
                event.location = list(event.location)
            for location in event.location:
                triple = {"subject": {"label": subject, "type": ["activity"], "uri": subject_uri},
                  "predicate": {"label": "location", "uri": "http://cltl.nl/leolani/n2mu/location"},
                  "object": {"label": location, "type": ["place"], "uri": ""}}
                triples.append(triple) 
        if event.time:
            if type(event.time)==str:
                event.time = [event.time]
            elif type(event.time)==tuple:
                event.time = list(event.time)
            for time in event.time:
                triple = {"subject": {"label": subject, "type": ["activity"], "uri": subject_uri},
                  "predicate": {"label": "time", "uri": "http://cltl.nl/leolani/n2mu/time"},
                  "object": {"label": time, "type": ["time"], "uri": ""}}
                triples.append(triple) 
    return triples



def get_triples(event, event_id):
    triples = []
    predicate_objects = []
    if 'activity' in event:
        subject = event['activity']
        subject_uri = "http://cltl.nl/leolani/n2mu/"+subject.replace(" ", "_")+str(event_id)
        if 'agent' in event:      
            if type(event['agent'])==str:
                event['agent'] = [event['agent']]
            for agent in event['agent']:
                triple = {"subject": {"label": subject, "type": ["activity"], "uri": subject_uri},
                  "predicate": {"label": "agent", "uri": "http://cltl.nl/leolani/n2mu/agent"},
                  "object": {"label":agent, "type": ["agent"], "uri": ""}}
                triples.append(triple) 
        if 'patient' in event:
            if type(event['patient'])==str:
                event['patient'] = [event['patient']]
            for patient in event['patient']:
                triple = {"subject": {"label": subject, "type": ["activity"], "uri": subject_uri},
                  "predicate": {"label": "patient", "uri": "http://cltl.nl/leolani/n2mu/patient"},
                  "object": {"label": patient, "type": ["agent", "object"], "uri": ""}}
                triples.append(triple) 
        if 'manner' in event:
            if type(event['manner'])==str:
                event['manner'] = [event['manner']]
            for manner in event['manner']:
                triple = {"subject": {"label": subject, "type": ["activity"], "uri": subject_uri},
                  "predicate": {"label": "manner", "uri": "http://cltl.nl/leolani/n2mu/manner"},
                  "object": {"label": manner, "type": ["property"], "uri": ""}}
                triples.append(triple) 
        if 'instrument' in event:
            if type(event['instrument'])==str:
                event['instrument'] = [event['instrument']]
            for instrument in event['instrument']:
                triple = {"subject": {"label": subject, "type": ["activity"], "uri": subject_uri},
                  "predicate": {"label": "instrument", "uri": "http://cltl.nl/leolani/n2mu/instrument"},
                  "object": {"label": instrument, "type": ["instrument"], "uri": ""}}
                triples.append(triple) 
        if 'location' in event:
            if type(event['location'])==str:
                event['location'] = [event['location']]
            for location in event['location']:
                triple = {"subject": {"label": subject, "type": ["activity"], "uri": subject_uri},
                  "predicate": {"label": "location", "uri": "http://cltl.nl/leolani/n2mu/location"},
                  "object": {"label": location, "type": ["place"], "uri": ""}}
                triples.append(triple) 
        if 'time' in event:
            if type(event['time'])==str:
                event['time'] = [event['time']]
            for time in event['time']:
                triple = {"subject": {"label": subject, "type": ["activity"], "uri": subject_uri},
                  "predicate": {"label": "time", "uri": "http://cltl.nl/leolani/n2mu/time"},
                  "object": {"label": time, "type": ["time"], "uri": ""}}
                triples.append(triple) 
    return triples
    
def get_capsules_from_turn (turn_data):
    capsules = []
    turn = turn_data['Input']
    event_data = turn_data['Output']
    chat_id = turn_data['chat']
    chat_date = parser.parse(turn_data['date'])
    turn_id = turn['turn']
    if event_data:
        event_id = random.random()
        triples = get_triples(event_data, event_id)
        offset = "0-"+str(len(turn["utterance"]))
        for triple in triples:
            capsule = { "chat": chat_id,
                "turn": turn_id,
                "author": {"label":turn['speaker'], "type": ["agent"], "uri":"http://cltl.nl/leolani/friends/"+turn['speaker']},
                "utterance": turn["utterance"],
                "utterance_type": UtteranceType.STATEMENT,
                "position": offset,
                "subject" : triple["subject"],
                "predicate" : triple["predicate"],
                "object" : triple["object"],
                "perspective":  get_dummy_perspective(),
                 "timestamp": datetime.combine(chat_date, datetime.now().time()),
                 "context_id": event_id
            }
            capsules.append(capsule)
    return capsules

def get_capsule_with_event_details_from_turn (turn_data):
    capsules = []
    turn = turn_data['Input']
    event_data = turn_data['Output']
    chat_id = turn_data['chat']
    chat_date = parser.parse(turn_data['date'])
    turn_id = turn['turn']
    if event_data:
        event_id = random.random()
        triples = get_triples(event_data, event_id)
        offset = "0-"+str(len(turn["utterance"]))
        capsule = { "chat": chat_id,
            "turn": turn_id,
            "author": {"label":turn['speaker'], "type": ["agent"], "uri":"http://cltl.nl/leolani/friends/"+turn['speaker']},
            "utterance": turn["utterance"],
            "utterance_type": UtteranceType.STATEMENT,
            "position": offset,
            "perspective":  get_dummy_perspective(),
             "timestamp": datetime.combine(chat_date, datetime.now().time()),
             "context_id": event_id
        }
        event_details_list = []
        for triple in triples:
            event_details_list.append({
                "subject" : triple["subject"],
                "predicate" : triple["predicate"],
                "object" : triple["object"]})
        capsule["event_details"] = event_details_list
    return capsule

def get_triples_from_turn(turn_data):
    event_data = turn_data['Output']
    triples = None
    if event_data:
        event_id = random.random()
        triples = get_triples(event_data, event_id)
    return triples

# TRIPLE EXAMPLE WITH EVENT DETAILS
# {"chat": 12,
#  "turn": 1,
#  "author": {"label": "piek", "type": ["person"], 'uri': "http://cltl.nl/leolani/friends/piek-1"},
#  "utterance": "John drinks beer",
#  "utterance_type": UtteranceType.STATEMENT,
#  "position": "0-15",
#  "event_details": [{
#      "subject": {"label": "drink", "type": ["event"],
#                  "uri": "http://cltl.nl/leolani/world/drink-2"
#                  },
#      "predicate": {"label": "hasActor", "uri": "sem:hasActor"},
#      "object": {"label": "john", "type": ["person"],
#                 "uri": "http://cltl.nl/leolani/world/john-1"
#                 }
#
#  },
#      {
#          "subject": {"label": "drink", "type": ["event"],
#                      "uri": "http://cltl.nl/leolani/world/drink-2"},
#          "predicate": {"label": "hasActor", "uri": "sem:hasActor"},
#          "object": {"label": "beer", "type": ["drink"],
#                     "uri": "http://cltl.nl/leolani/world/beer"}
#      },
#      {
#          "subject": {"label": "drink", "type": ["event"],
#                      "uri": "http://cltl.nl/leolani/world/drink-2"},
#          "predicate": {"label": "hasPlace", "uri": "sem:hasPlace"},
#          "object": {"label": "pub", "type": ["place"],
#                     "uri": "http://cltl.nl/leolani/world/pub"}
#      },
#      {
#          "subject": {"label": "drink", "type": ["event"],
#                      "uri": "http://cltl.nl/leolani/world/drink-2"},
#          "predicate": {"label": "hasTime", "uri": "sem:hasTime"},
#          "object": {"label": "8-3-2026", "type": ["date"],
#                     "uri": date_iri}
#      }
#  ],
#  "perspective": {
#      "certainty": 1,
#      "polarity": 1,
#      "sentiment": 1
#  },
#  "timestamp": datetime.combine(start_date, datetime.now().time()),
#  "context_id": context_id
#  }

# EXAMPLE OF THE SRL OUTPUT WHICH IS THE INPUT FOR CREATING CAPSULES
# conversation turn:

        # {
        #     "chat": 255,
        #     "date": "2014,Feb,04",
        #     "human": "Mehmet",
        #     "Input": {
        #         "turn": 6,
        #         "speaker": "Mehmet",
        #         "utterance": "I\u2019ll give that a try. I've also noticed that my afternoon snacks are sometimes not very healthy."
        #     },
        #     "Output": {
        #         "activity": "Provides suggestions on managing blood sugar, portion control, and importance of Mediterranean diet.",
        #         "agent": [
        #             "doctor",
        #             "health advisor"
        #         ],
        #         "patient": [
        #             "Mehmet"
        #         ],
        #         "instrument": [
        #             "medication management",
        #             "dietary suggestions"
        #         ],
        #         "manner": [
        #             "supportive",
        #             "encouraging"
        #         ],
        #         "location": [],
        #         "time": "during a medical consultation"
        #     }
        # }

# CLASSICAL EXAMPLES OF TRIPLES

# capsule:
# {  # CARL SAYS CANNOT SEE HIS PILLS
#         "chat": 1,
#         "turn": 1,
#         "author": {"label": "carl", "type": ["person"], 'uri': "http://cltl.nl/leolani/friends/carl-1"},
#         "utterance": "I need to take my pills, but I cannot find them.",
#         "utterance_type": UtteranceType.STATEMENT,
#         "position": "0-25",
#         "subject": {"label": "carl", "type": ["person"], 'uri': "http://cltl.nl/leolani/world/carl-1"},
#         "predicate": {"label": "see", "uri": "http://cltl.nl/leolani/n2mu/see"},
#         "object": {"label": "pills", "type": ["object", "medicine"], 'uri': "http://cltl.nl/leolani/world/pills-1"},
#         "perspective": {"certainty": 1, "polarity": -1, "sentiment": -1},
#         "timestamp": datetime.combine(start_date, datetime.now().time()),
#         "context_id": context_id
#     }


# event_capsule:
# {  # CARL SAYS CANNOT SEE HIS PILLS
#         "chat": 1,
#         "turn": 1,
#         "author": {"label": "carl", "type": ["person"], 'uri': "http://cltl.nl/leolani/friends/carl-1"},
#         "utterance": "I need to take my pills, but I cannot find them.",
#         "utterance_type": UtteranceType.STATEMENT,
#         "position": "0-25",
#         "event_details: {
#         "subject": {"label": "see", "type": ["person"], 'uri': "http://cltl.nl/leolani/world/see-1"},
#         "predicate": {"label": "hasActor", "uri": "sem:hasActor"},
#         "object": {"label": "pills", "type": ["object", "medicine"], 'uri': "http://cltl.nl/leolani/world/pills-1"}
#          },
#         "perspective": {"certainty": 1, "polarity": -1, "sentiment": -1},
#         "timestamp": datetime.combine(start_date, datetime.now().time()),
#         "context_id": context_id
#     }