# Even-centric knowledge extraction from conversations

This project demonstrates how to use ChatGPT to extract event centric triples from conversations and push these to an episodic Knowledge Graph.

The conversations are taken from:

data/conversations.json

This file has short simulated synthetic conversations between a diabetes II patient and a lifestyle coach.


## Features

- Event extraction from conversations using OpenAI's LLM
- Semantic Role Labeling (SRL) for structured event representation
- Hierarchical clustering of event elements
- Event Knowledge Graph (EKG) population
- Statistical analysis and visualization of event patterns


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

We use a sliding window through each conversation that prompts ChatGPT if "speaker1" (the human user) has uttered something. It takes the preceeding context of turns to extract any activity and the semantic roles.

The annotations are saved in a pickle file and as a json file.


2. Converting event data to event-centric triples and saving these in the Knowledge Graph

We first load the pickle file with the annotations by ChatGPT. Next we convert the event data  into even-centric triples in which the subject is the activity and the semantic roles are the predicates. The objects are the slot fillers for the roles. Activities get unique identities per conversation.

The triples are included in so-called capsules that provide the communication layer for the data, such as the context, the chat, the turn, the timestamp, the author and the author perspective.

After converting all the data, the capsules are pushed to the event-centric Knowledge Graph.


## Core Components

### Event Extraction (llm_event_triples_openai.py)
- Extracts structured event information from conversations
- Uses OpenAI's language models for semantic analysis
- Identifies activities, agents, patients, instruments, manner, location, and time

### Knowledge Graph Population (populate_ekg.py)
- Converts extracted events into knowledge graph format
- Manages context and temporal information
- Integrates with triple store database

### Statistical Analysis (srl_statistics.py)
- Generates frequency statistics for event elements
- Creates hierarchical visualizations
- Analyzes patterns in extracted information

### Hierarchical Organization (words_to_hierarchy.py)
- Builds hierarchical structures from phrases
- Uses semantic similarity for clustering
- Generates visualizations of concept hierarchies

## Dependencies

- OpenAI API
- sentence-transformers
- networkx
- matplotlib
- sklearn
- scipy
- requests
- pydantic
- tqdm

## Installation

1. Clone the repository
2. Install required packages:

```aiignore
bash pip install -r requirements.txt
```
3. Set up OpenAI API key
4. Configure graph database (GraphDB) endpoint

## Usage

1. Process conversations and extract events:

```aiignore
python from cltl.llm_event_extraction import LLM_EventExtraction
extractor = LLM_EventExtraction() annotations = extractor.annotate_all_turns_in_conversation(conversation_data)
```

2. Populate knowledge graph:

python from cltl.populate_ekg import get_scenarios_from_srl_annotations
scenarios = get_scenarios_from_srl_annotations(annotated_conversations)

3. Generate statistics and visualizations:

python from cltl.srl_statistics import get_statistics, get_analysis_for_srl_dict
stats = get_statistics(annotated_conversations, threshold=3)


## Output

The system generates:
- JSON files with extracted events
- Knowledge graph in triple store format
- Statistical analysis in JSON format
- Hierarchical visualizations in PNG format
- Event pattern analysis results

## License

This project is licensed under the [LICENSE](LICENSE) file in the repository.

## Contributing

Contributions are welcome. Please read the contributing guidelines before making a pull request.
