
import json
import requests
from cltl.brain.long_term_memory import LongTermMemory
from cltl.commons.discrete import UtteranceType
from cltl.brain.infrastructure.api import Perspective, Triple, RDFBase, Entity, Predicate
from tqdm import tqdm
from random import getrandbits
from pathlib import Path
import events_to_capsules
from dateutil import parser
from datetime import date, datetime
from enum import Enum
from emotion_extraction import GoEmotionDetector
import zipfile

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
                turn_capsule = events_to_capsules.get_capsule_with_event_details_from_turn_with_conversationa_context_similarity_match_and_time(conversational_context=conversational_context, turn_data=turn, emotion_detector=emotion_detector)
                if turn_capsule:
                    capsules.append(turn_capsule)
                ### Old code that extracts separate capsules for each triple
                # turn_capsules = events_to_capsules.get_capsules_from_turn(turn)
                # capsules.extend(turn_capsules)
            if capsules:
                scenario = (scenario_context, capsules)
                scenarios.append(scenario)
        ###break
    return scenarios


def _serialize_enum(val):
    """Serialize a Perspective field: handles None, single Enum, or list of Enum/scalar values."""
    if val is None:
        return None
    if isinstance(val, list):
        return [e.name if isinstance(e, Enum) else e for e in val]
    if isinstance(val, Enum):
        return val.name
    return val


class CapsuleEncoder(json.JSONEncoder):
    """Serializes capsule objects: Perspective/Triple/RDFBase → dict, Enum → name, datetime → ISO."""

    def _preprocess(self, obj):
        """Walk the object graph and convert all non-standard types before encoding.

        Enum subclasses that also inherit str/int are serialized by Python's JSON
        encoder as their raw value, bypassing default(). Preprocessing fixes that.
        """
        if isinstance(obj, Perspective):
            return {
                "certainty": _serialize_enum(obj.certainty),
                "polarity": _serialize_enum(obj.polarity),
                "sentiment": _serialize_enum(obj.sentiment),
                "emotion": _serialize_enum(obj.emotion),
                "level": _serialize_enum(obj.level),
            }
        if isinstance(obj, Triple):
            return {
                "subject": self._preprocess(obj.subject),
                "predicate": self._preprocess(obj.predicate),
                "complement": self._preprocess(obj.complement),
            }
        if isinstance(obj, Entity):
            return {"id": str(obj.id), "label": str(obj.label), "types": obj.types}
        if isinstance(obj, Predicate):
            return {"id": str(obj.id), "label": str(obj.label)}
        if isinstance(obj, RDFBase):
            return {"id": str(obj.id), "label": str(obj.label)}
        if isinstance(obj, Enum):
            return obj.name
        if isinstance(obj, datetime):   # datetime first — it is a subclass of date
            return obj.isoformat()
        if isinstance(obj, date):
            return obj.isoformat()
        if isinstance(obj, dict):
            return {k: self._preprocess(v) for k, v in obj.items()}
        if isinstance(obj, (list, tuple)):
            return [self._preprocess(item) for item in obj]
        return obj

    def encode(self, obj):
        return super().encode(self._preprocess(obj))

    def iterencode(self, obj, _one_shot=False):
        return super().iterencode(self._preprocess(obj), _one_shot)

def main():
    INPUT_ZIP = Path("../../data/events_srl_typed.json.zip")
    ### Initialisation of the path for logging and of the GraDB repository for saving the data
    # Create folders
    scenario_filepath = Path('../../data/')
    graph_filepath = scenario_filepath / Path('graph/')
    graph_filepath.mkdir(parents=True, exist_ok=True)

    # Create brain connection
    brain = LongTermMemory(address="http://localhost:7200/repositories/diabetes_event_details_and_types",  # Location to save accumulated graph
                           log_dir=graph_filepath,  # Location to save step-wise graphs
                           clear_all=True)  # To start from an empty brain

    model_path = "AnasAlokla/multilingual_go_emotions"
    #  Languages: Arabic, English, French, Spanish, Dutch, Turkish
    emotion_detector = GoEmotionDetector(model=model_path)

    ## Input is a JSON file that has the conversations, the meta data and the SRL results on a turn by turn basis
    print(f"Loading {INPUT_ZIP} …")
    with zipfile.ZipFile(INPUT_ZIP) as z:
        inner = [n for n in z.namelist() if n.endswith(".json")][0]
        with z.open(inner) as f:
            annotated_conversations = json.load(f)

    print('Total number of annotated conversations', len(annotated_conversations))
    print(annotated_conversations[0])
    ### A scenario has a context_capsule that identifies the scenario and a list of capsules extracted for a single conversation that need to be added to the brain.
    # The context capsule contains contextual information about the scenario (e.g. location, date, etc.) and
    # the capsules contain the information that needs to be added to the brain (e.g. triples, event details, etc.)
    scenarios = get_scenarios_from_srl_annotations(annotated_conversations, emotion_detector)
    print('Total nr of scenarios', len(scenarios))
    f = open(scenario_filepath / "capsules_with_event_details.json", "w")
    json.dump(scenarios, f, indent=4, cls=CapsuleEncoder)

    # Loop through the scenarios
    for (context_capsule, conversation_capsules) in tqdm(scenarios):
        print('Conversation id', context_capsule['context_id'], 'Total number of capsules extracted for this conversation', len(conversation_capsules))        # Create context
        brain.capsule_context(context_capsule)
        # Add information to the brain
        for capsule in conversation_capsules:
            print('chat', capsule['chat'], 'out of ', len(scenarios), 'turn', capsule['turn'], 'out of', len(conversation_capsules), 'turns')
           # brain.capsule_statement(capsule, reason_types=True, return_thoughts=False, create_label=True)
            brain.capsule_event(capsule, reason_types=True, return_thoughts=False, create_label=True)

if __name__ == '__main__':
    main()