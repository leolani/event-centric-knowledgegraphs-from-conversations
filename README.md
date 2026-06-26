# Event-Centric Knowledge Extraction from Conversations

This project demonstrates how to use an LLM (OpenAI ChatGPT) to extract event-centric triples from conversations and push these to an episodic Knowledge Graph.

The conversations are taken from:

`data/conversations.json`

This file has short simulated synthetic conversations between a diabetes II patient and a lifestyle coach.


## Features

- Event extraction from conversations using OpenAI's LLM
- Semantic Role Labeling (SRL) for structured event representation
- Entity type classification of semantic role fillers using OpenAI
- Temporal expression resolution to absolute dates using OpenAI
- EventSeries typing for recurring and vague temporal events
- Emotion detection per utterance (multilingual: Arabic, English, French, Spanish, Dutch, Turkish)
- Hierarchical clustering of event elements
- Ontology hierarchy generation in TTL format
- Event Knowledge Graph (EKG) population
- Statistical analysis and visualization of event patterns
- Butterfly timeline visualization of events per persona


## Pipeline

### 1. Event extraction from conversations

The notebook **llm_event_extraction.ipynb** first loads the conversations. Next, it uses a client to prompt ChatGPT to extract activities and their semantic roles:

```python
from llm_event_triples_openai import LLM_EventExtraction
```

This class is defined in **llm_event_triples_openai.py**.

ChatGPT saves the result using a data class:

```python
class EventTripleExtraction(BaseModel):
    activity: str
    agent: list[str]
    patient: list[str]
    instrument: list[str]
    manner: list[str]
    location: list[str]
    time: str
```

We use a sliding window through each conversation that prompts ChatGPT when "speaker1" (the human user) has uttered something. It takes the preceding context of turns to extract any activity and the semantic roles.

The annotations are saved in a pickle file and as a JSON file.


### 2. Time expression resolution

**llm_resolve_time_expressions.py** reads the event SRL data and calls OpenAI to resolve relative time expressions (e.g., "last week", "every morning") to absolute dates relative to each conversation's date. Each time expression is also assigned a temporal type:

- `absolute` — a specific date
- `relative` — relative to conversation date
- `recurring` — a repeating pattern
- `vague` — imprecise reference

Output: `data/event_srl_time_resolved.json.zip`


### 3. Role type classification

**classify_roles.py** classifies the string values of agent, patient, instrument, and location role fillers into entity types using OpenAI (GPT-4o-mini). Results are cached in `data/role_type_cache.json`.

Output: `data/events_srl_typed.json.zip`


### 4. Converting event data to capsules and saving to the Knowledge Graph

**events_to_capsules.py** converts event data into event-centric triples where the subject is the activity and the semantic roles are predicates. Activities receive unique identities per conversation.

Key functions:
- `get_triples` — basic triple generation
- `get_triples_with_types` — typed triple generation with resolved time expressions; activities whose time is `recurring` or `vague` are typed as `EventSeries`
- `get_utterance_perspective` — extracts certainty, polarity, sentiment, emotion level, and detected emotions from each utterance using the multilingual GoEmotions model (`AnasAlokla/multilingual_go_emotions`)

The triples are packaged into capsules that carry context: chat and turn IDs, author, utterance, timestamp, and perspective (including emotions).

**populate_ekg.py** and **populate_ekg_with_types.py** push these capsules to the Event-Centric Knowledge Graph via the `LongTermMemory` API.


### 5. Ontology hierarchy generation

**generate_hierarchy_ttl.py** reads activity type counts, role type counts, and temporal type counts from CSV files and generates a TTL ontology hierarchy.

Output: `data/eckg_hierarchy.ttl`

**visualise_hierarchy.py** renders the TTL hierarchy as a PNG diagram.

Output: `doc/eckg_hierarchy.png`


### 6. Statistical analysis and visualization

**srl_statistics.py** generates frequency statistics for event elements and creates hierarchical visualizations.

**doc/plot_butterfly_timeline.py** produces vertical butterfly timeline plots that visualize event timelines per persona, queried from the Knowledge Graph. The plot layout is:

- **Y-axis** — time (earliest at top)
- **Centre line** — activities plotted as ◆ diamonds, coloured by activity type
- **Left / right wings** — emotion markers per speaker, radiating negative (left) or positive (right)
- **Ovals around diamonds** — indicate a grounded time (`ns1Time`); shape encodes precision of the time grounding (`p` column):
  - `dateTime` → tight circle (solid, dark)
  - `rangeTime` → wider oval (solid, lighter)
  - `recurringTime` → wider oval (solid, lighter still)
  - `vagueTime` → widest oval (dotted, lightest)
- If `ns1Time` is present it is used to position the activity on the timeline; otherwise the original `time` column is used.

```bash
python doc/plot_butterfly_timeline.py --input_file doc/query-result-<persona>.csv --dim a4
```

Supported paper sizes: `a4`, `a3`, `a1`.

Output: `doc/query-result-<persona>_butterfly_timeline.png`

**emotion_by_author_table.py** extracts emotion counts per author from the capsule data.

Output: `data/emotion_by_author_counts.csv`


## Core Components

| Module | Description |
|---|---|
| `llm_event_triples_openai.py` | Extracts structured events from conversations via OpenAI |
| `llm_resolve_time_expressions.py` | Resolves relative time expressions to absolute dates |
| `classify_roles.py` | Classifies entity types of semantic role fillers |
| `events_to_capsules.py` | Converts events to capsules with perspective and emotion |
| `populate_ekg.py` | Populates the EKG from basic capsules |
| `populate_ekg_with_types.py` | Populates the EKG with typed roles and emotion |
| `emotion_extraction.py` | Multilingual emotion detection using GoEmotions |
| `generate_hierarchy_ttl.py` | Generates TTL ontology hierarchy from type counts |
| `visualise_hierarchy.py` | Renders the ontology hierarchy as a PNG diagram |
| `emotion_by_author_table.py` | Produces per-author emotion frequency tables |
| `srl_statistics.py` | Frequency statistics and hierarchical visualizations |
| `doc/plot_butterfly_timeline.py` | Butterfly timeline visualization per persona with time-grounding ovals |
| `words_to_hierarchy.py` | Builds hierarchical structures from phrases via semantic similarity |


## Data Files

| File | Description |
|---|---|
| `data/conversations.json` | Input conversations |
| `data/event_srl_time_resolved.json.zip` | Events with resolved time expressions |
| `data/events_srl_typed.json.zip` | Events with entity-typed role fillers |
| `data/capsules_with_event_details.json.zip` | Capsules with full event details |
| `data/activity_counts.csv/json` | Activity frequency counts |
| `data/activity_type_counts.csv` | Activity type frequency |
| `data/role_type_counts*.csv/json` | Role type frequency per role |
| `data/temporal_type_counts.csv` | Temporal type frequency |
| `data/time_expression_counts.csv/json` | Time expression frequency |
| `data/emotion_by_author_counts.csv` | Emotion counts per author |
| `data/role_type_cache.json` | Cache for OpenAI role type classifications |
| `data/eckg_hierarchy.ttl` | Ontology hierarchy in Turtle format |
| `data/personas.json` | Persona definitions |


## Dependencies

- OpenAI API (GPT-4o / GPT-4o-mini)
- sentence-transformers
- transformers (GoEmotions model)
- networkx
- matplotlib
- sklearn
- scipy
- requests
- pydantic
- tqdm
- pandas
- rdflib
- dateutil

## Installation

1. Clone the repository
2. Install required packages:

```bash
pip install -r requirements.txt
```

3. Set up OpenAI API key:

```bash
export OPENAI_API_KEY=sk-...
```

4. Configure GraphDB endpoint


## Usage

1. Extract events from conversations:

```python
from cltl.llm_event_extraction import LLM_EventExtraction
extractor = LLM_EventExtraction()
annotations = extractor.annotate_all_turns_in_conversation(conversation_data)
```

2. Resolve time expressions:

```bash
python src/cltl/llm_resolve_time_expressions.py
```

3. Classify role types:

```bash
python src/cltl/classify_roles.py
```

4. Populate knowledge graph with typed events:

```python
from cltl.populate_ekg_with_types import get_scenarios_from_srl_annotations
scenarios = get_scenarios_from_srl_annotations(annotated_conversations, emotion_detector)
```

5. Generate statistics and visualizations:

```python
from cltl.srl_statistics import get_statistics, get_analysis_for_srl_dict
stats = get_statistics(annotated_conversations, threshold=3)
```

6. Generate ontology hierarchy:

```bash
python src/cltl/generate_hierarchy_ttl.py
python src/cltl/visualise_hierarchy.py
```


## Output

The system generates:
- JSON files with extracted events and typed roles
- Resolved time expressions with temporal type annotations
- Knowledge graph in triple store (GraphDB) format
- Ontology hierarchy in TTL and PNG format
- Statistical analysis in JSON/CSV format
- Butterfly timeline visualizations per persona (PNG)
- Per-author emotion frequency table (CSV)

## License

This project is licensed under the [LICENSE](LICENSE) file in the repository.

## Contributing

Contributions are welcome. Please read the contributing guidelines before making a pull request.
