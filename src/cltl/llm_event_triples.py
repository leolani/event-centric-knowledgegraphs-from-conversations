from langchain_ollama import ChatOllama
import json
from datetime import datetime
from openai import OpenAI

#https://ollama.com/models
#ollama pull qwen3:1.7b
predicates = ["sem:hasActor", "sem:hasTimne", "sem:hasPlace"]

class LLM_EventExtraction:
    
    def __init__(self,  model="qwen3:1.7b", predicates=[], max_context=5):
        
        self._client = ChatOllama(
            model=model,
            temperature= 0.0,
            think=False
            #num_predict = 20, ## max number of tokens to predict
        )
        self._max_context = max_context
        self._history = []
        self._instruct = []
        self.create_label_instruct2(predicates)

    def create_label_instruct2(self, predicates =[]):
        prompt = '''You will receive a conversation of turns in JSON format between two speakers called speaker1 and speaker2.
You need to extract the main activities that are mentioned in the conversation. For each activity, extract who, what, where and when. The result should be in JSON format.

Do not output any other text than the JSON.

<start of examples>
Example 1:
    Input: [{"speaker": "speaker1", "utterance": "I graduated in January in Amsterdam."}, {"speaker": "speaker2", "utterance": "I graduated in February in Madrid."}]
    Output: [
                {"activity": "graduate", "who": "speaker1", "where": "Amsterdam", "when": "January"},
                {"activity": "graduate", "who": "speaker2", "where": "Madrid", "when": "February"}
            ]
Example 2:
    Input: [{"speaker": "speaker1", "utterance": "My sister cycled in January to Amsterdam."}, 
            {"speaker": "speaker2", "utterance": "My mother ran a marathon in February in Madrid."}]
    Output: [
                {"activity": "cycle", "who": "speaker1-sister", "where": "Amsterdam", "when": "January"},
                {"activity": "marathon", "who": "speaker2-mother", "where": "Madrid", "when": "February"}
            ]

<end of examples>
'''
        
    def create_label_instruct(self, predicates =[]):
        prompt = '''You will receive a conversation of turns in JSON format between two speakers called speaker1 and speaker2.
You need to extract event-centric triples from the conversation consisting of a subject, predicate, and object.
Each triple should capture the essence of a statement by the speaker.
The subject should be the action, state, or property (e.g., "read", "be-from", "like-not").
The predicate is one of the following labels that reflect basic semantic roles: {}.
If the predicate is {}, then the object can be the speaker, the hearer, a third person, animal, or object.
If the predicate is {}, then the object should be a place.
If the predicate is {}, then the object should be a date or time.
The triple elements can be based on the last three turns.
Map "I" and "you" as well as "your" and "mine" to speaker1 and speaker2 depending on who is speaking.
Do not output any other text than the JSON.
<start of examples>
Example 1:
    user: {{"speaker": "speaker1", "utterance": "I am from Amsterdam."}}
    output: [
        {{"subject": "be-from", "predicate": "hasActor", "object": "speaker1"}},
        {{"subject": "be-from", "predicate": "hasPlace", "object": "Amsterdam"}}
    ]
Example 2:
    user: {{"speaker": "speaker2", "utterance": "You are reading a book."}} 
    output: [
        {{"subject": "read", "predicate": "hasActor", "object": "speaker1"}},
        {{"subject": "read", "predicate": "hasPatient", "object": "book"}}
    ]
Example 3:
    user: {{"speaker": "speaker1", "utterance": "You hate dogs."}}
    output: [
        {{"subject": "hate", "predicate": "hasActor", "object": "speaker2"}},
        {{"subject": "hate", "predicate": "hasPatient", "object": "dogs"}}
    ]
Example 4:
    user: {{"speaker": "speaker1", "utterance": "I do not like cheese."}}
    output: [
        {{"subject": "like-not", "predicate": "hasActor", "object": "speaker1"}},
        {{"subject": "like-not", "predicate": "hasPatient", "object": "cheese"}}
    ]
<end of examples>
'''.format(", ".join(predicates), predicates[0], predicates[1], predicates[2])
        
        self._instruct = self._instruct = [{"role": "system", "content": prompt}]
        print("My instructions are:", self._instruct)

    def annotate_conversation2(self, input=[]):
        report = 1
        annotations = []
        counter = 0
        start = datetime.now()
        previous = start
        print("Annotating a conversation with {} utterances".format(len(input)))
        for text in input:
            self._history.append({"role": "user", "content": "Input: {}".format(text)})

        prompt = self._instruct+self._history
        print(prompt)
        response = self._client.invoke(prompt)
        
        ### We need to remove the <think></think> part from the output
        end_of_think = response.content.find("</think>")
        answer = response
        if end_of_think>0:
            think = response.content[:end_of_think+8]
            answer = response.content[end_of_think+8:].replace("\n", "")
        annotation={"Input": text, "Output": answer}
        print(annotation)
        return annotations
        
    def annotate_conversation(self, input=[]):
        report = 1
        annotations = []
        counter = 0
        start = datetime.now()
        previous = start
        print("Annotating a conversation with {} utterances".format(len(input)))
        for text in input:
            annotation = self.annotate(text)
            annotations.append(annotation)
            counter+=1
            if counter % report == 0:
                now  = datetime.now()
                print('Processed', report, 'in', (now - previous).seconds, 'seconds')
                print("Processed", counter, "turns in total out of", len(input))
                previous = now
        return annotations
  
    def annotate(self, utterance):
        annotation ={}
        self._history.append({"role": "user", "content": "Input: {}".format(utterance)})

        ## if the history exceeds the maximum context length, we trim it by one
        if len(self._history)>self._max_context:
            self._history = self._history[1:]
    
        prompt = self._instruct+self._history
        response = self._client.invoke(prompt)
        
        ### We need to remove the <think></think> part from the output
        end_of_think = response.content.find("</think>")
        answer = response
        if end_of_think>0:
            think = response.content[:end_of_think+8]
            answer = response.content[end_of_think+8:].replace("\n", "")
        annotation={"Input": utterance, "Output": answer}
        print(annotation)
        return annotation

if __name__ == "__main__":
    predicates = ["sem:hasActor", "sem:hasTime", "sem:hasPlace"]
    events = ["happy", "fun", "sad", "depressed"]
    input = [{"speaker": "speaker1", "utterance": "I am very happy"}, 
             {"speaker": "speaker2", "utterance": "I am surprised"}, 
             {"speaker": "speaker1", "utterance": "What can I do about it?"}, 
             {"speaker": "speaker2", "utterance": "Now I am having real fun."}, 
             {"speaker": "speaker1", "utterance": "It makes me sad and depressed"}, 
             {"speaker": "speaker2", "utterance": "Sorry to hear that"}]
    llm_extractor  = LLM_EventExtraction(predicates=predicates, max_context=3)
    annotations = llm_extractor.annotate_conversation(input)
    for annotation in annotations:
        print(annotation)
                         
