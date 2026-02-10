import json
from json import JSONEncoder
from datetime import datetime
from pydantic import BaseModel
from openai import OpenAI
#https://platform.openai.com/docs/guides/structured-outputs?api-mode=chat

#predicates = ["sem:hasActor", "sem:hasTimne", "sem:hasPlace"]
path = "/Users/piek/Library/Mobile Documents/com~apple~CloudDocs/iCloud-mac/servers-key/openaikey1.txt"
file = open(path, "r")
key = file.read()


class EventTripleExtraction(BaseModel):
    activity: str
    agent: list[str]
    patient: list[str]
    instrument: list[str]
    manner: list[str]
    location: list[str]
    time: str
            
class LLM_EventExtraction:
    
    def __init__(self):
        self._client = OpenAI(api_key=key)
        self._history = []
        self._instruct = []
        self.create_label_instruct()

    def create_label_instruct(self):
        prompt = '''You will receive a conversation in JSON format between two speakers: one a diabetes patient and one a lifestyle coach. 
        The conversation contains the name of the diabetes patient and date on which the conversation took place.
You need to extract activities and conditions of the diabetes patient from the conversation. 
Only extract Activities of Daily Life in which the diabetes patient participates or conditions of the patient's lifestyle.
Try to represent as much details about the Activity or the Condition from the conversation.
For each activity or condition, extract who, what, how, where and when. The result should be in JSON format.
Do not output any other text than the JSON.

<start of examples>
Example 1:
    Input: {
        "chat": 6,
        "human": "Jan",
        "date": "2010,Dec,13",
        "turns": [
            {
                "turn": 1,
                "speaker": "Jan",
                "utterance": "I've been noticing tingling in my feet lately. Is this something common with Type 2 Diabetes?"
            }
            ]
            }
    Output: [
                {"activity": "tingling in my feet", "agent": "Jan",  "time": "lately"}
            ]
Example 2:
    Input:     {
        "chat": 7,
        "human": "Jan",
        "date": "2012,Jan,31",
        "turns": [
                {
                    "turn": 1,
                    "speaker": "agent",
                    "utterance": "Jan, I understand that you've been managing your Type 2 Diabetes for quite some time now. Can you tell me more about your current medication regimen?"
                },
                {
                    "turn": 2,
                    "speaker": "Fatima",
                    "utterance": "I take metformin tablets twice daily, and also an evening insulin injection. Besides, I take a daily aspirin for heart health, as advised by my doctor."
                }
            ]
            }
    Output: [
                {"activity": "take", "agent": "Fatima", "patient": "metformin tablets", "time": "twice daily"},
                {"activity": "take", "agent": "Fatima", "patient": "aspirin", "time": "daily"}
            ]
<end of examples>
'''
        
    def annotate_speaker1_conversation(self, input={}):
        annotations = []
        self._history = []
        print("Annotating a conversation with {} utterances".format(len(input['turns'])))
        for index, turn in enumerate(input['turns']):
            self._history.append({"role": "user", "content": "Input: {}".format(turn)})
            if not turn['speaker']=='agent':
                prompt = self._instruct+self._history
                completion = self._client.beta.chat.completions.parse(   ### had to add .beta. in the call
                        model="gpt-4o-2024-08-06",
                        messages=prompt,
                        response_format=EventTripleExtraction)
                response = completion.choices[0].message.parsed
                annotation={"chat": input['chat'], "date": input["date"], "human": input["human"], "Input": turn, "Output": response}
                annotations.append(annotation)
        return annotations

    def annotate_all_turns_in_conversation(self, input={}):
        annotations = []
        self._history = []
        print("Annotating a conversation with {} utterances".format(len(input['turns'])))
        for index, turn in enumerate(input['turns']):
            self._history.append({"role": "user", "content": "Input: {}".format(turn)})
            prompt = self._instruct+self._history
            completion = self._client.beta.chat.completions.parse(   ### had to add .beta. in the call
                    model="gpt-4o-2024-08-06",
                    messages=prompt,
                    response_format=EventTripleExtraction)
            response = completion.choices[0].message.parsed
            annotation={"chat": input['chat'], "date": input["date"], "human": input["human"], "Input": turn, "Output": response}
            annotations.append(annotation)
        return annotations

if __name__ == "__main__":
    input = [{"speaker": "speaker1", "utterance": "I am very happy"}, 
             {"speaker": "speaker2", "utterance": "I am surprised"}, 
             {"speaker": "speaker1", "utterance": "What can I do about it?"}, 
             {"speaker": "speaker2", "utterance": "Now I am having real fun."}, 
             {"speaker": "speaker1", "utterance": "It makes me sad and depressed"}, 
             {"speaker": "speaker2", "utterance": "Sorry to hear that"}]
    llm_extractor  = LLM_EventExtraction()
    annotations = llm_extractor.annotate_full_conversation(input)
    for annotation in annotations:
        print(annotation)
    annotations = llm_extractor.annotate_speaker1_conversation(input)
    for annotation in annotations:
        print(annotation)
                         
