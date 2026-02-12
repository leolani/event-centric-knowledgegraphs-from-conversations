
import json
import requests
from cltl.brain.long_term_memory import LongTermMemory
from cltl.commons.discrete import UtteranceType
from tqdm import tqdm
from random import getrandbits
from pathlib import Path
import events_to_capsules
from dateutil import parser


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

def main():
    f = open("/Users/piek/Desktop/Diabetes/load_datasets/diabetes/event_srl.json", "r")
    annotated_conversations = json.load(f)
    print(len(annotated_conversations))
    print(annotated_conversations[0])
    scenarios = get_scenarios_from_srl_annotations(annotated_conversations)
    print(len(scenarios))

    # Create folders
    scenario_filepath = Path('/Users/piek/Desktop/Diabetes/load_datasets//diabetes/')
    graph_filepath = scenario_filepath / Path('graph/')
    graph_filepath.mkdir(parents=True, exist_ok=True)

    # Create brain connection
    brain = LongTermMemory(address="http://localhost:7200/repositories/diabetes",  # Location to save accumulated graph
                           log_dir=graph_filepath,  # Location to save step-wise graphs
                           clear_all=True)  # To start from an empty brain

    # Loop through capsules
    all_capsules = []
    for (context_capsule, content_capsules) in tqdm(scenarios):
        print(context_capsule['context_id'], len(content_capsules))        # Create context
        response = brain.capsule_context(context_capsule)

        # Add information to the brain
        for capsule in content_capsules:
            all_capsules.append(capsule)
            if capsule['utterance_type'] == UtteranceType.STATEMENT:
                response = brain.capsule_statement(capsule, reason_types=True, return_thoughts=False, create_label=True)

    # Save capsules
    f = open(scenario_filepath / "capsules.json", "w")
    json.dump(all_capsules, f)

if __name__ == '__main__':
    main()