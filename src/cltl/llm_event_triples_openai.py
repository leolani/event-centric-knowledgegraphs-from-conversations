from openai import OpenAI
import prompts as prompts
#https://platform.openai.com/docs/guides/structured-outputs?api-mode=chat


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
        self._instruct = [{"role": "system", "content": prompts.prompt_conversational_srl_activity_type}]

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
