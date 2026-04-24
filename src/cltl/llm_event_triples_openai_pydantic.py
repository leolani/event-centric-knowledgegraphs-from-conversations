import json
from openai import OpenAI
from typing import Optional, Literal
from pydantic import BaseModel
import prompts as prompts

#https://platform.openai.com/docs/guides/structured-outputs?api-mode=chat

#predicates = ["sem:hasActor", "sem:hasTimne", "sem:hasPlace"]
path = "../../../openaikey1.txt"
file = open(path, "r")
key = file.read()


class EventTripleExtraction(BaseModel):
    model_config = {"json_schema_mode": "validation"}
    
    activity: str
    activity_type: prompts.ActivityType
    agent: Optional[list[str]]=[]
    patient: Optional[list[str]]=[]
    instrument: Optional[list[str]]=[]
    manner: Optional[list[str]]=[]
    location: Optional[list[str]]=[]
    time: Optional[list[str]]=[]
    
    @classmethod
    def to_openai_function(cls):
        """Convert the Pydantic model to OpenAI function definition for tool use."""
        return {
            "type": "function",
            "function": {
                "name": "extract_event",
                "description": "Extract structured event details with semantic roles from text.",
                "parameters": cls.model_json_schema()
            }
        }


class EventExtractions(BaseModel):
    model_config = {"json_schema_mode": "validation"}
    
    extractions: list[EventTripleExtraction]
    
    @classmethod
    def to_openai_function(cls):
        """Convert the Pydantic model to OpenAI function definition for tool use."""
        return {
            "type": "function",
            "function": {
                "name": "extract_events",
                "description": "Extract list of structured event details with semantic roles from text.",
                "parameters": cls.model_json_schema()
            }
        }


class LLM_EventExtraction:
    
    def __init__(self):
        self._client = OpenAI(api_key=key)
        self._history = []
        self._instruct = [{"role": "system", "content": prompts.prompt_conversational_srl_activity_type}]

    def process_input(self, turn):
        # 2. Define the OpenAI function call parameters
        function_schema = EventExtractions.to_openai_function()

        self._history.append({"role": "user", "content": "Input: {}".format(turn)})

        # 3. Prepare the messages
        messages = self._instruct+self._history

        # 4. Call the OpenAI API with the tool definition
        # You can set tool_choice to "required" if you insist the model calls the function,
        # or "auto" to let it decide.
        response = self._client.chat.completions.create(
            model="gpt-3.5-turbo-0125",  # or your specific model
            messages=messages,
            tools=[function_schema],
            tool_choice = "required"  # Force function call otherwise use :auto"
        )

        # 5. Process the response
        response_message = response.choices[0].message

        tool_calls = response_message.tool_calls

        if tool_calls:
            # The model invoked the function
            available_functions = {
                "extract_events": EventExtractions,
            }
            for tool_call in tool_calls:
                function_name = tool_call.function.name
                function_to_call = available_functions[function_name]
                function_args = json.loads(tool_call.function.arguments)
                # print('function_name', function_name)
                # print('function_to_call', function_to_call)
                # print('function_args', function_args)
                # Parse the response into a Pydantic model
                try:
                    structured_output = function_to_call(**function_args)
                except Exception as e:
                    print("Error parsing function output:", e)
                    structured_output = None
                if structured_output is not None:
                    return structured_output.extractions
                else:
                    return None
        else:
            # Fallback if the model didn't call the function
            return response_message.content

    def annotate_all_turns_in_conversation(self, input={}):
        annotations = []
        self._history = []
        print("Annotating a conversation with {} utterances".format(len(input['turns'])))
        for index, turn in enumerate(input['turns']):
            print('turn', turn)
            response = self.process_input(turn['utterance'])
            if response:
                annotation={"chat": input['chat'], "date": input["date"], "human": input["human"], "Input": turn, "Output": response}
                annotations.append(annotation)
        return annotations

if __name__ == "__main__":
    llm_extractor  = LLM_EventExtraction()

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
            print(annotation['Output'])
