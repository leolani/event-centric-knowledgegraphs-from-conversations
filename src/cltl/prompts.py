prompt_conversational_srl = '''You will receive a conversation in JSON format between two speakers: one a diabetes patient and one a lifestyle coach. 
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
activity_types = ["exercise", "take_food", "take_drink", "advise", "social", "treatment", "physical condition", "social condition", "mental condition"]

prompt_conversational_srl_activity_type = '''You will receive a conversation in JSON format between two speakers: a diabetes patient and a lifestyle coach. 
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
                    {"activity": "tingling in my feet", "activity_type": "physical condition", "agent": ["Jan"],  "location": ["feet"], "time": ["lately"]}
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
                    {"activity": "take", "activity_type": "treatment", "agent": ["Fatima"], "patient": ["metformin tablets"], "time": "twice daily"},
                    {"activity": "take", "activity_type": "treatment", "agent": ["Fatima"], "patient": ["aspirin"], "time": ["daily"]}
                    {"activity": "take", "activity_type": "treatment", "agent": ["Fatima"], "patient": ["insulin injection"], "time": ["evening"]}
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
                    {"activity": "lunch", "activity_type":"take_food", "agent": ["Fatima"], "patient": ["grilled chicken"], "time": ["yesterday"]},
                    {"activity": "lunch",  "activity_type":"take_food","agent": ["Fatima"], "patient": ["salad"], "time": ["yesterday"]},
                    {"activity": "dinner",  "activity_type":"take_food","agent": ["Fatima"], "patient": ["fish"], "time": ["yesterday"]},
                    {"activity": "dinner",  "activity_type":"take_food","agent": ["Fatima"], "patient": ["steamed vegetables"], "time": ["yesterday"]},
                    {"activity": "experience",  "activity_type":"physical condition", "agent": ["Fatima"], "patient": ["weight gain"], "time": ["recently"]},
                    {"activity": "experience",  "activity_type":"physical condition", "agent": ["Fatima"], "patient": ["dizziness"], "time": ["occasionally"]}
                ]  
    <end of examples>
    '''
