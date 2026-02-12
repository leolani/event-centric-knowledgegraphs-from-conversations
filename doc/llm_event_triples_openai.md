# LLM Event Triples OpenAI (llm_event_triples_openai.py)

This module provides functionality for extracting structured event information from conversations using OpenAI's language models. It specifically focuses on processing conversations between diabetes patients and lifestyle coaches.

## Dependencies

- json
- pydantic
- openai
- datetime

## Core Components

### EventTripleExtraction Model

A Pydantic BaseModel that defines the structure for extracted event information:

```aiignore
python class EventTripleExtraction(BaseModel): activity: str agent: list[str] patient: list[str] instrument: list[str] manner: list[str] location: list[str] time: str
```

## Output Format

For each turn, produces an annotation in the format:

```aiignore
json { "chat": <chat_id>, "date": <conversation_date>, "human": <patient_name>, "Input": { "turn": <turn_number>, "speaker":  , "utterance": <utterance_text> }, "Output": { "activity": <extracted_activity>, "agent": [<agent_list>], "patient": [<patient_list>], "instrument": [<instrument_list>], "manner": [<manner_list>], "location": [<location_list>], "time": <time_expression> } }
```


## Usage Example

```aiignore
python
# Initialize extractor
llm_extractor = LLM_EventExtraction()
# Process a single conversation
conversation = { "chat": 1, "human": "John", "date": "2023,Dec,15", "turns": [ {  }
# Extract events from all turns
annotations = llm_extractor.annotate_all_turns_in_conversation(conversation)
# Or extract only patient turns
patient_annotations = llm_extractor.annotate_speaker1_conversation(conversation)
```

## Notes

- Uses OpenAI's API for event extraction
- Requires valid OpenAI API key
- Focuses on medical/health-related activities and conditions
- Supports both selective (patient-only) and complete conversation processing
- Maintains conversation context through chat history

