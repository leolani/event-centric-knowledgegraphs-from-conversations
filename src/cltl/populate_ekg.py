
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


def get_scenarios_from_srl_annotations(annotated_conversations):
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
            for turn in conversation:
                turn_capsules = events_to_capsules.get_capsules_from_turn(turn)
                capsules.extend(turn_capsules)
            if capsules:
                scenario = (scenario_context, capsules)
                scenarios.append(scenario)
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
    f = open("../../data/event_srl.json", "r")
    annotated_conversations = json.load(f)
    print(len(annotated_conversations))
    print(annotated_conversations[0])
    scenarios = get_scenarios_from_srl_annotations(annotated_conversations)
    print(len(scenarios))

    # Create folders
    scenario_filepath = Path('../../data/')
    graph_filepath = scenario_filepath / Path('graph/')
    graph_filepath.mkdir(parents=True, exist_ok=True)

    # Create brain connection
    brain = LongTermMemory(address="http://localhost:7200/repositories/sandbox",  # Location to save accumulated graph
                           log_dir=graph_filepath,  # Location to save step-wise graphs
                           clear_all=True)  # To start from an empty brain

    # Loop through capsules
    all_capsules = []
    for (context_capsule, content_capsules) in tqdm(scenarios):
        print(context_capsule['context_id'], len(content_capsules))        # Create context
        brain.capsule_context(context_capsule)
        all_capsules.append(context_capsule)
        # Add information to the brain
        for capsule in content_capsules:
            print('chat', capsule['chat'], 'turn', capsule['turn'])
            all_capsules.append(capsule)
            brain.capsule_statement(capsule, reason_types=True, return_thoughts=False, create_label=True)
        break

    f = open(scenario_filepath / "capsules.json", "w")
    safe_capsules = deep_copy_without_circular(all_capsules)
    json.dump(safe_capsules, f, indent=4)


if __name__ == '__main__':
    main()