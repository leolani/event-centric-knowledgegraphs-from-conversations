
import json
import requests
from cltl.brain.long_term_memory import LongTermMemory
from cltl.commons.discrete import UtteranceType
from tqdm import tqdm
from random import getrandbits
from pathlib import Path
import events_to_capsules
from dateutil import parser
from datetime import datetime
from types import MappingProxyType
from emotion_extraction import GoEmotionDetector

def get_scenarios_from_srl_annotations(annotated_conversations, emotion_detector):
    # Define contextual features
    place_id = getrandbits(8)
    location = requests.get("https://ipinfo.io").json()

    scenarios = []
    for conversation in annotated_conversations:
        if len(conversation) > 0:
            scenario_context = {"context_id": conversation[0]['chat'],
                                "date": parser.parse(conversation[0]['date']),
                                "place": "Piek's office",
                                "place_id": place_id,
                                "country": location['country'],
                                "region": location['region'],
                                "city": location['city']}
            capsules = []
            ### We extract caosules for each turn to that we can ground them to specific turns
            ### We could also create a function that aggregates all triples related to a single event (subject)
            ### and create a capsule per event for the complete conversation. This would reduce the number of claims and capsules even further.
            ### Problem with that is that the source of the claims becomes indistinguishable.

            conversational_context= {}
            for turn in conversation:
                ### new code that combines triples from a single turn into one single capsule
              #  turn_capsule = events_to_capsules.get_capsule_with_event_details_from_turn(turn, emotion_detector)
                turn_capsule = events_to_capsules.get_capsule_with_event_details_from_turn_with_conversationa_context(conversational_context=conversational_context, turn_data=turn, emotion_detector=emotion_detector)
                if turn_capsule:
                    capsules.append(turn_capsule)
                ### Old code that extracts separate capsules for each triple
                # turn_capsules = events_to_capsules.get_capsules_from_turn(turn)
                # capsules.extend(turn_capsules)
            if capsules:
                scenario = (scenario_context, capsules)
                scenarios.append(scenario)
       # break
    return scenarios

class CustomEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        elif hasattr(obj, '__dict__'):
            return obj.__dict__
        return super().default(obj)


class CustomEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        elif isinstance(obj, MappingProxyType):
            return dict(obj)
        elif hasattr(obj, '__dict__'):
            return obj.__dict__
        elif isinstance(obj, (list, tuple)):
            return list(obj)
        elif isinstance(obj, set):
            return list(obj)
        try:
            return json.JSONEncoder.default(self, obj)
        except TypeError:
            return str(obj)

def deep_copy_without_circular(obj, memo=None):
    if memo is None:
        memo = set()

    # Check for basic types that can be returned as-is
    if isinstance(obj, (str, int, float, bool, type(None))):
        return obj

    # Handle datetime objects
    if isinstance(obj, datetime):
        return obj.isoformat()

    # Get object's id to check for circular references
    obj_id = id(obj)
    if obj_id in memo:
        return "<circular reference>"
    memo.add(obj_id)

    try:
        if isinstance(obj, dict):
            return {k: deep_copy_without_circular(v, memo.copy())
                   for k, v in obj.items()}
        elif isinstance(obj, (list, tuple)):
            return [deep_copy_without_circular(x, memo.copy())
                   for x in obj]
        elif isinstance(obj, MappingProxyType):
            return dict(obj)
        elif hasattr(obj, '__dict__'):
            # For objects, only copy their dictionary
            return {k: deep_copy_without_circular(v, memo.copy())
                   for k, v in obj.__dict__.items()
                   if not k.startswith('_')}  # Skip private attributes
        else:
            # If we can't handle it, convert to string
            return str(obj)
    except Exception:
        return str(obj)


def main():

    ### Initialisation of the path for logging and of the GraDB repository for saving the data
    # Create folders
    scenario_filepath = Path('../../data/')
    graph_filepath = scenario_filepath / Path('graph/')
    graph_filepath.mkdir(parents=True, exist_ok=True)

    # Create brain connection
    brain = LongTermMemory(address="http://localhost:7200/repositories/diabetes_event_details",  # Location to save accumulated graph
                           log_dir=graph_filepath,  # Location to save step-wise graphs
                           clear_all=True)  # To start from an empty brain

    model_path = "AnasAlokla/multilingual_go_emotions"
    #  Languages: Arabic, English, French, Spanish, Dutch, Turkish
    emotion_detector = GoEmotionDetector(model=model_path)

    ## Input is a JSON file that has the conversations, the meta data and the SRL results on a turn by turn basis
    f = open("../../data/event_srl.json", "r")
    annotated_conversations = json.load(f)
    print('Total number of annotated conversations', len(annotated_conversations))
    print(annotated_conversations[0])
    ### A scenario has a context_capsule that identifies the scenario and a list of capsules extracted for a single conversation that need to be added to the brain.
    # The context capsule contains contextual information about the scenario (e.g. location, date, etc.) and
    # the capsules contain the information that needs to be added to the brain (e.g. triples, event details, etc.)
    scenarios = get_scenarios_from_srl_annotations(annotated_conversations, emotion_detector)
    print('Total nr of scenarios', len(scenarios))
    # Loop through the scenarios
    all_capsules = []
    for (context_capsule, conversation_capsules) in tqdm(scenarios):
        print('Conversation id', context_capsule['context_id'], 'Total number of capsules extracted for this conversation', len(conversation_capsules))        # Create context
        brain.capsule_context(context_capsule)
        all_capsules.append(context_capsule)
        # Add information to the brain
        for capsule in conversation_capsules:
            print('chat', capsule['chat'], 'out of ', len(scenarios), 'turn', capsule['turn'], 'out of', len(conversation_capsules), 'turns')
            all_capsules.append(capsule)
           # brain.capsule_statement(capsule, reason_types=True, return_thoughts=False, create_label=True)
            brain.capsule_event(capsule, reason_types=True, return_thoughts=False, create_label=True)

        break

    f = open(scenario_filepath / "capsules_with_event_details.json", "w")
    safe_capsules = deep_copy_without_circular(all_capsules)
    json.dump(safe_capsules, f, indent=4)


if __name__ == '__main__':
    main()