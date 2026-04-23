import json
from json import JSONEncoder
from datetime import datetime
from pydantic import BaseModel
from openai import OpenAI
#https://platform.openai.com/docs/guides/structured-outputs?api-mode=chat

#predicates = ["sem:hasActor", "sem:hasTimne", "sem:hasPlace"]
path = "../../../openaikey1.txt"
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
#        self.create_label_instruct()
        self.create_label_instruct_v2()

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
                            "utterance": "Fatima, I understand that you've been managing your Type 2 Diabetes for quite some time now. Can you tell me more about your current medication regimen?"
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
        self._instruct = [{"role": "system", "content": prompt}]

    def create_label_instruct_v2(self):
        prompt = '''You will receive a conversation in JSON format between two speakers: a diabetes patient and a lifestyle coach. 
            The conversation contains the name of the diabetes patient and the date on which the conversation took place.
            You need to extract activities and conditions of the diabetes patient from the last turn in the conversation. You can use the preceding turns as the context.
            Only extract Activities of Daily Life in which the diabetes patient participates or physical, social or mentional conditions of the patient in relation to the patient's lifestyle.
            Try to represent as much details about the Activity or the Condition from the conversation.
            For each activity or condition, extract the WHAT as activity, the TYPE of activity or condition as activity_type, the  WHO as agent, the WHOM as patient, the HOW as manner, the WITH as instrument, WHERE as location and WHEN as time. 
            Always include the activity_type in the output, which can be either "exercise", "take_food", "take_drink", "advise", "social", "treatment", "physical condition", "social condition" or "mental condition".
            
            **Required Fields:**
            - activity: the activity or condition that the patient is doing or experiencing.
            - activity_type: the specific type or category of the activity.
            - agent: The entity performing the activity.
        
            **Optional Fields:**
            - patient: The entity affected by the activity.
            - instrument: The tool or means used.
            - location: Where the activity takes place.
            - time: When the activity occurs.
        
            Text to analyze:
            {input_text}
            
            Output the results in the specified JSON format. Do not output any other text than the JSON. The output JSON MUST include fields for the activity, activity_type and agent, and can optionally include patient, instrument, location and time if that information is present in the text.
        
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
                            {"activity": "tingling in my feet", "activity_type": "physical condition", "agent": "Jan",  "location": "feet", "time": "lately"}
                        ]
            Example 2:
                Input:     {
                    "chat": 7,
                    "human": "Fatima",
                    "date": "2012,Jan,31",
                    "turns": [
                            {
                                "turn": 1,
                                "speaker": "agent",
                                "utterance": "Fatima, I understand that you've been managing your Type 2 Diabetes for quite some time now. Can you tell me more about your current medication regimen?"
                            },
                            {
                                "turn": 2,
                                "speaker": "Fatima",
                                "utterance": "I take metformin tablets twice daily, and also an evening insulin injection. Besides, I take a daily aspirin for heart health, as advised by my doctor."
                            }
                        ]
                        }
                Output: [
                            {"activity": "take", "activity_type": "treatment", "agent": "Fatima", "patient": "metformin tablets", "time": "twice daily"},
                            {"activity": "take", "activity_type": "treatment", "agent": "Fatima", "patient": "aspirin", "time": "daily"}
                            {"activity": "take", "activity_type": "treatment", "agent": "Fatima", "patient": "insulin injection", "time": "evening"}
                        ]
            
            Example 3:
            Input:     {
                "chat": 8,
                "human": "Jan",
                "date": "2012,Jan,31",
                "turns": [
                        {       "turn": 1,
                                "speaker": "agent",
                                "utterance": "What did you eat yesterday"
                        },
                        {       "turn": 2,
                                "speaker": "Fatima",
                                "utterance": "Yes, for lunch, I had grilled chicken with salad, and for dinner, I cooked a fish with some steamed vegetables."
                        },
                        {       "turn": 3,
                                "speaker": "agent",
                                "utterance": "Any other worries?"
                        },
                        {
                            "turn": 4,
                            "speaker": "Fatima",
                            "utterance": "I do have some concerns about the side effects of my medications, especially the insulin injection. I've been experiencing some weight gain and occasional dizziness. I'm not sure if these are common side effects or if I should discuss them with my doctor."
                        }
                    ]
                }
                Output: [
                            {"activity": "lunch", "activity_type":"take_food", "agent": "Fatima", "patient": "grilled chicken", "time": "yesterday"},
                            {"activity": "lunch",  "activity_type":"take_food","agent": "Fatima", "patient": "salad", "time": "yesterday"},
                            {"activity": "dinner",  "activity_type":"take_food","agent": "Fatima", "patient": "fish", "time": "yesterday"},
                            {"activity": "dinner",  "activity_type":"take_food","agent": "Fatima", "patient": "steamed vegetables", "time": "yesterday"},
                            {"activity": "experience",  "activity_type":"physical condition", "agent": "Fatima", "patient": "weight gain", "time": "recently"},
                            {"activity": "experience",  "activity_type":"physical condition", "agent": "Fatima", "patient": "dizziness", "time": "occasionally"}
                        ]  
            <end of examples>
            '''
        self._instruct = [{"role": "system", "content": prompt}]

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
    llm_extractor  = LLM_EventExtraction()

    # input = [{"speaker": "speaker1", "utterance": "I am very happy"},
    #          {"speaker": "speaker2", "utterance": "I am surprised"},
    #          {"speaker": "speaker1", "utterance": "What can I do about it?"},
    #          {"speaker": "speaker2", "utterance": "Now I am having real fun."},
    #          {"speaker": "speaker1", "utterance": "It makes me sad and depressed"},
    #          {"speaker": "speaker2", "utterance": "Sorry to hear that"}]
    #
    # annotations = llm_extractor.annotate_full_conversation(input)
    # for annotation in annotations:
    #     print(annotation)
    # annotations = llm_extractor.annotate_speaker1_conversation(input)
    # for annotation in annotations:
    #     print(annotation)

    chats = [{
        "chat": 254,
        "human": "Mehmet",
        "date": "2013,Jan,31",
        "turns": [
            {
                "turn": 1,
                "speaker": "Mehmet",
                "utterance": "I've been reading about how different diets can impact my blood sugar levels. Recently, I've heard about the Mediterranean diet being beneficial. Do you think it's suitable for me?"
            },
            {
                "turn": 2,
                "speaker": "agent",
                "utterance": "The Mediterranean diet can indeed be beneficial for managing Type 2 Diabetes, Mehmet. Its emphasis on whole grains, healthy fats, fruits, vegetables, and lean proteins can help stabilize blood sugar levels. Have you tried integrating any of its elements into your diet already?"
            },
            {
                "turn": 3,
                "speaker": "Mehmet",
                "utterance": "Not entirely, but I've been incorporating more olive oil and fish into my meals. Is there anything specific I should avoid or be cautious about?"
            },
            {
                "turn": 4,
                "speaker": "agent",
                "utterance": "That's a great start. You might want to also focus on portion control to maintain a balanced calorie intake and avoid added sugars and refined grains. This diet\u2019s high fiber content can particularly help in managing your blood sugar."
            },
            {
                "turn": 5,
                "speaker": "Mehmet",
                "utterance": "I see, but I enjoy having traditional Turkish meals, especially during family gatherings. Can these fit within the Mediterranean guidelines?"
            },
            {
                "turn": 6,
                "speaker": "agent",
                "utterance": "Absolutely. Many traditional Turkish dishes already align well with the Mediterranean diet. You can focus on dishes that include plenty of vegetables, legumes, and lean meats, and try to swap out less healthy ingredients for more wholesome options where possible."
            },
            {
                "turn": 7,
                "speaker": "Mehmet",
                "utterance": "That sounds manageable. I'll explore more recipes and perhaps even share them with my family for our gatherings. Thanks for the advice."
            },
            {
                "turn": 8,
                "speaker": "agent",
                "utterance": "You're welcome, Mehmet! It's wonderful that you\u2019re involving your family in your health journey. This can make managing your condition more enjoyable and sustainable."
            }
        ]
    },
        {
            "chat": 32,
            "human": "Rudolf",
            "date": "2014,Apr,08",
            "turns": [
                {
                    "turn": 1,
                    "speaker": "agent",
                    "utterance": "Rudolf, let's talk about your meals today. What was your breakfast like?"
                },
                {
                    "turn": 2,
                    "speaker": "Rudolf",
                    "utterance": "For breakfast, I had a bowl of oatmeal along with an apple."
                },
                {
                    "turn": 3,
                    "speaker": "agent",
                    "utterance": "That's a healthy choice, Rudolf. How about lunch and dinner? Did you include lean proteins and vegetables?"
                },
                {
                    "turn": 4,
                    "speaker": "Rudolf",
                    "utterance": "Yes, for lunch, I had grilled chicken with salad, and for dinner, I cooked a fish with some steamed vegetables."
                },
                {
                    "turn": 5,
                    "speaker": "agent",
                    "utterance": "Sounds good. Including lean proteins and vegetables in your meals is beneficial for managing your blood sugar levels. However, don't forget to also include whole grains and fiber-rich foods for balanced meals."
                },
                {
                    "turn": 6,
                    "speaker": "Rudolf",
                    "utterance": "I will remember to do that. Also, I need advice on snacks. What would you recommend?"
                },
                {
                    "turn": 7,
                    "speaker": "agent",
                    "utterance": "Snacking on fruits and nuts or seeds is a good option, they can help prevent spikes in your blood sugar levels. Remember to consume in moderation, especially nuts and seeds, as they are high in calories. Drink plenty of water throughout the day as well."
                },
                {
                    "turn": 8,
                    "speaker": "agent",
                    "utterance": "Good morning, Rudolf. I noticed that you haven't logged your glucose levels in the app for a couple of days. Is everything alright?"
                },
                {
                    "turn": 9,
                    "speaker": "Rudolf",
                    "utterance": "I got caught up with work and forgot. Also, it's a bit of a hassle to do it every day."
                },
                {
                    "turn": 10,
                    "speaker": "agent",
                    "utterance": "It's understandable that it can feel tedious, Rudolf, but remember, regular monitoring is essential in managing your diabetes effectively."
                }
            ]
        }
    ]
    for chat in chats:
        annotations = llm_extractor.annotate_all_turns_in_conversation(chat)
        for annotation in annotations:
            print(annotation)
