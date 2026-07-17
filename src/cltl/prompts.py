from string import Template

from data_type import (
    ActivityType,
    RoleType,
    ResultType,
    EmotionLabel,
    Factuality,
    Certainty,
    TemporalType,
    RecurrencePattern,
    quoted_values,
)

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

prompt_conversational_srl_activity_type = '''You will receive a conversation in JSON format between two speakers: a diabetes patient and a lifestyle coach.
    The conversation contains the name of the diabetes patient and the date on which the conversation took place.
    You need to extract activities and conditions of the diabetes patient from the last turn in the conversation. You can use the preceding turns as the context.
    Only extract Activities of Daily Life in which the diabetes patient participates or physical, social or mental conditions of the patient in relation to the patient's lifestyle.
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
                    {"activity": "take", "activity_type": "treatment", "agent": ["Fatima"], "patient": ["metformin tablets"], "time": ["twice daily"]},
                    {"activity": "take", "activity_type": "treatment", "agent": ["Fatima"], "patient": ["aspirin"], "time": ["daily"]},
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

_prompt_conversational_srl_annotation_template = Template('''You will receive a conversation in JSON format between two speakers: a diabetes patient and a lifestyle coach.
    The conversation contains the name of the diabetes patient, the date on which the conversation took place, and a list of turns.
    You need to extract activities and conditions of the diabetes patient from the LAST turn in the conversation only. Use the preceding turns purely as context, e.g. to recognize that the last turn continues talking about an activity or condition that was already introduced earlier.
    Only extract Activities of Daily Life in which the diabetes patient participates, or physical, social or mental conditions of the patient in relation to the patient's lifestyle.
    The activity or condition itself must be represented as a noun phrase copied verbatim from the utterance (e.g. "cycling", "insulin injection", "weight gain"), not as a verb.

    Every enumerated field below is restricted to exactly the values listed (the same closed vocabularies used by the annotation tool's dropdowns) — never invent a value outside these lists. Where the list includes "other", use it only when none of the other values fit; roles or fields whose lists do NOT include "other" (result, recurrence_pattern) should simply be omitted or left null instead of forcing a bad fit.

    Output a JSON array. Each element of the array is one annotation entry for the last turn, structured as follows:

    **perspective** (required, identical on every entry for this turn): the speaker's stance on their own utterance.
    - emotion: one of $emotion_values
    - factuality: one of $factuality_values
    - certainty: one of $certainty_values

    **activity** (required):
    - If this is the first time the activity or condition is mentioned in the conversation: {"value": <verbatim phrase>, "offset": <int>, "length": <int>, "type": <activity_type>, "activity_id": "chat{N}.{M}"}, where N is the chat number and M increases by 1 for every new activity, in the order it is first introduced.
    - If the last turn continues talking about an activity or condition that was already introduced in an earlier turn (visible in the given context): output only {"activity_id": "chat{N}.{M}"}, reusing the existing id, without value, offset, length or type. Any new role information from the last turn (e.g. a new time or location) is still attached to this entry.
    - activity_type must be one of: $activity_type_values.

    **Semantic roles** (all optional, all arrays; only include a role if the text of the LAST turn supports it):
    - agent, patient, instrument, manner, location: arrays of {"value": <verbatim phrase>, "type": <role_type>, "offset": <int>, "length": <int>}, where role_type is one of $role_type_values.
    - result: array of {"value": <verbatim phrase>, "type": <result_type>, "offset": <int>, "length": <int>}, where result_type is one of $result_type_values.
    - time: array of {"value": <verbatim phrase>, "offset": <int>, "length": <int>}.
    - time_resolved: array of {"time_expression": <verbatim phrase matching a "time" entry>, "temporal_type": <temporal_type>, "absolute_date": <"YYYY-MM-DD" or null>, "date_range_start": <"YYYY-MM-DD" or null>, "date_range_end": <"YYYY-MM-DD" or null>, "recurrence_pattern": <recurrence_pattern or null>}, grounding each time expression to a calendar date using the conversation's date as the reference point. temporal_type is one of $temporal_type_values. recurrence_pattern is one of $recurrence_pattern_values when the time expression clearly recurs on one of those patterns, otherwise null (e.g. "twice daily" is best captured as recurrence_pattern "daily" plus the free-text time value "twice daily").

    Every "offset" and "length" MUST be computed against the utterance text of the LAST turn only (0-indexed character offset, length in characters), and the substring of the utterance at [offset : offset + length] must exactly equal "value".
    Do not output any other text than the JSON array.

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
                    {
                        "perspective": {"emotion": "nervousness", "factuality": "expect", "certainty": "uncertain"},
                        "activity": {"value": "tingling in my feet", "offset": 19, "length": 19, "type": "physical condition", "activity_id": "chat6.1"},
                        "agent": [{"value": "I", "type": "person", "offset": 0, "length": 1}],
                        "patient": [], "instrument": [], "manner": [], "location": [], "result": [],
                        "time": [{"value": "lately", "offset": 39, "length": 6}],
                        "time_resolved": [{"time_expression": "lately", "temporal_type": "range", "absolute_date": null, "date_range_start": "2010-12-06", "date_range_end": "2010-12-13", "recurrence_pattern": null}]
                    }
                ]

    Example 2 (continuation of the same conversation, turn 2 refers back to the activity introduced in turn 1):
        Input: {
            "chat": 6,
            "human": "Jan",
            "date": "2010,Dec,13",
            "turns": [
                {
                    "turn": 1,
                    "speaker": "Jan",
                    "utterance": "I've been noticing tingling in my feet lately. Is this something common with Type 2 Diabetes?"
                },
                {
                    "turn": 2,
                    "speaker": "Jan",
                    "utterance": "I think it has actually gotten worse over the past week, especially in my toes."
                }
                ]
                }
        Output: [
                    {
                        "perspective": {"emotion": "disappointment", "factuality": "confirm", "certainty": "certain"},
                        "activity": {"activity_id": "chat6.1"},
                        "agent": [{"value": "I", "type": "person", "offset": 0, "length": 1}],
                        "patient": [], "instrument": [], "manner": [],
                        "location": [{"value": "toes", "type": "other", "offset": 74, "length": 4}],
                        "result": [],
                        "time": [{"value": "the past week", "offset": 42, "length": 13}],
                        "time_resolved": [{"time_expression": "the past week", "temporal_type": "range", "absolute_date": null, "date_range_start": "2010-12-06", "date_range_end": "2010-12-13", "recurrence_pattern": null}]
                    }
                ]

    Example 3:
        Input: {
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
                    {
                        "perspective": {"emotion": "neutral", "factuality": "confirm", "certainty": "certain"},
                        "activity": {"value": "metformin tablets", "offset": 7, "length": 17, "type": "medicine", "activity_id": "chat7.1"},
                        "agent": [{"value": "I", "type": "person", "offset": 0, "length": 1}],
                        "patient": [], "instrument": [], "manner": [], "location": [], "result": [],
                        "time": [{"value": "twice daily", "offset": 25, "length": 11}],
                        "time_resolved": [{"time_expression": "twice daily", "temporal_type": "recurring", "absolute_date": null, "date_range_start": null, "date_range_end": null, "recurrence_pattern": "daily"}]
                    },
                    {
                        "perspective": {"emotion": "neutral", "factuality": "confirm", "certainty": "certain"},
                        "activity": {"value": "insulin injection", "offset": 58, "length": 17, "type": "medicine", "activity_id": "chat7.2"},
                        "agent": [], "patient": [], "instrument": [], "manner": [], "location": [], "result": [],
                        "time": [{"value": "evening", "offset": 50, "length": 7}],
                        "time_resolved": []
                    },
                    {
                        "perspective": {"emotion": "neutral", "factuality": "confirm", "certainty": "certain"},
                        "activity": {"value": "aspirin", "offset": 101, "length": 7, "type": "medicine", "activity_id": "chat7.3"},
                        "agent": [{"value": "I", "type": "person", "offset": 86, "length": 1}],
                        "patient": [], "instrument": [], "manner": [], "location": [],
                        "result": [{"value": "heart health", "type": "goal", "offset": 113, "length": 12}],
                        "time": [{"value": "daily", "offset": 95, "length": 5}],
                        "time_resolved": []
                    }
                ]

    Example 4 (only the LAST turn is annotated; turn 2's food items are ignored because they belong to an earlier turn):
        Input: {
            "chat": 8,
            "human": "Fatima",
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
                    {
                        "perspective": {"emotion": "nervousness", "factuality": "confirm", "certainty": "uncertain"},
                        "activity": {"value": "weight gain", "offset": 128, "length": 11, "type": "physical condition", "activity_id": "chat8.1"},
                        "agent": [{"value": "I", "type": "person", "offset": 100, "length": 1}],
                        "patient": [], "instrument": [], "manner": [], "location": [], "result": [], "time": [],
                        "time_resolved": []
                    },
                    {
                        "perspective": {"emotion": "nervousness", "factuality": "confirm", "certainty": "uncertain"},
                        "activity": {"value": "dizziness", "offset": 155, "length": 9, "type": "physical condition", "activity_id": "chat8.2"},
                        "agent": [{"value": "I", "type": "person", "offset": 100, "length": 1}],
                        "patient": [], "instrument": [], "manner": [], "location": [], "result": [],
                        "time": [{"value": "occasional", "offset": 144, "length": 10}],
                        "time_resolved": []
                    }
                ]
    <end of examples>
    ''')

prompt_conversational_srl_annotation = _prompt_conversational_srl_annotation_template.substitute(
        emotion_values=quoted_values(EmotionLabel),
        factuality_values=quoted_values(Factuality),
        certainty_values=quoted_values(Certainty),
        activity_type_values=quoted_values(ActivityType),
        role_type_values=quoted_values(RoleType),
        result_type_values=quoted_values(ResultType),
        temporal_type_values=quoted_values(TemporalType),
        recurrence_pattern_values=quoted_values(RecurrencePattern),
)
