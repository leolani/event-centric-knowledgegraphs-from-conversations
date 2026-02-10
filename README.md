# Even-centric knowledge extraction from conversations

This project demonstrates how to use ChatGPT to extract event centric triples from conversations and push these to an episodic Knowledge Graph.

The conversations are taken from:

diabetes/final_few_shot_raw_conversations_gpt4.txt

This file has short simulated synthetic conversations between a diabetes II patient and a lifestyle coach.

1. Obtaining the event data from the conversations

The notebook **llm_event_extraction.ipynb** first loads the conversations. Next, it uses a client to prompt ChatGPT to extract activities and their semantic roles:

from llm_event_triples_openai import LLM_EventExtraction

This class is defined in **llm_event_triples_openai.py**.

ChatGPT saves the input as a dictionary and the result using a data class:

class EventTripleExtraction(BaseModel):
    activity: str
    agent: list[str]
    patient: list[str]
    instrument: list[str]
    manner: list[str]
    location: list[str]
    time: str

We use a sliding window through each conversation that prompts ChatGPT if "speaker1" (the human user) has uttered something. It takes the preceeding context of three turns to extract any activity and the semantic roles.

The annotations are saved in a pickle file.


2. Converting event data to event-centric triples and saving these in the Knowledge Graph

We first load the pickle file with the annotations by ChatGPT. Next we convert the event data  into even-centric triples in which the subject is the activity and the semantic roles are the predicates. The objects are the slot fillers for the roles. Activities get unique identities per conversation.

The triples are included in so-called capsules that provide the communication layer for the data, such as the context, the chat, the turn, the timestamp, the author and the author perspective.

After converting all the data, the capsules are pushed to the event-centric Knowledge Graph.
