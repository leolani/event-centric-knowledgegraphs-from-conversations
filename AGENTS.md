# AGENTS.md - Guidance for AI Coding Agents

## Architecture Overview

This is a **dual-project system** for extracting and representing episodic knowledge from conversations:

1. **event-centric-knowledgegraphs-from-conversations** (this project):
   - Extracts structured events from conversation data using OpenAI LLM
   - Converts events into RDF triples via Semantic Role Labeling (SRL)
   - Pushes data to knowledge graph via cltl.brain

2. **cltl-knowledgerepresentation** (dependency, separate repo):
   - `LongTermMemory` class: main API interface for graph operations
   - Manages RDF triple store with GraphDB backend
   - Implements reasoners (trust, type, location) and thought generation

## Critical Data Flow Pattern

All knowledge enters the system as **capsules** - JSON dictionaries with structure:

```python
# Context capsule (first item in list)
{"context_id": int, "date": str, "place": str, "place_id": int, 
 "country": str, "region": str, "city": str}

# Statement/event capsules (list of dict items)
{"chat": int, "turn": int, "author": {"label": str, "type": list, "uri": str},
 "utterance": str, "utterance_type": "STATEMENT|QUESTION|EXPERIENCE",
 "subject": {...}, "predicate": {"label": str, "uri": str}, 
 "object": {...}, "perspective": {"certainty": 0-1, "polarity": -1 to 1, 
 "sentiment": -1 to 1, "emotion": list or 0}}
```

Example: `examples/capsules/baking.json`

For the event extraction capsules do not contain a single triple but an event_details element that can contain a list of triples, typically all containing the same event IRI as the subject, while the predicates are roles and the objects filler for these roles.

Here is an example of such a capsule with event_detailds:

```python
{"chat": 0, "turn": 0, "author": {"label": "Alice", "type": ["person"], "uri": "http://cltl.nl/leolani/world/alice"},
 "utterance": "I baked a cake yesterday.", "utterance_type": "STATEMENT",
 "event_details": [
    {"subject": {"label": "baking event", "type": ["event"], "uri": "http://cltl.nl/leolani/world/baking-event-1"},
        "predicate": {"label": "agent", "uri": "http://cltl.nl/leolani/n2mu/agent"}, 
     "object": {"label": "Alice", "type": ["person"], "uri": "http://cltl.nl/leolani/world/alice"}},
    {"subject": {"label": "baking event", "type": ["event"], "uri": "http://cltl.nl/leolani/world/baking-event-1"},
        "predicate": {"label": "patient", "uri": "http://cltl.nl/leolani/n2mu/patient"}, 
     "object": {"label": "cake", "type": ["food"], "uri": "http://cltl.nl/leolani/world/cake"}},
    {"subject": {"label": "baking event", "type": ["event"], "uri": "http://cltl.nl/leolani/world/baking-event-1"},
        "predicate": {"label": "time", "uri": "http://cltl.nl/leolani/n2mu/time"}, 
     "object": {"label": "yesterday", "type": ["time"], "uri": "http://cltl.nl/leolani/world/yesterday"}}
 ],
 "perspective": {"certainty": 1, "polarity": 1, "sentiment": 1, "emotion": ["joy"]}}
``` 

## Event Extraction Pipeline

**Input**: Raw conversation JSON → **Process**: LLM + SRL → **Output**: Capsules → Knowledge Graph

1. **LLM Extraction** (`llm_event_triples_openai.py`):
   - Uses `EventTripleExtraction` Pydantic model (defines structure)
   - Prompts ChatGPT with context window to extract: activity, agent, patient, instrument, manner, location, time
   - Results stored as pickle + JSON for analysis

2. **Capsule Conversion** (`events_to_capsules.py`):
   - Converts SRL annotations to capsule format
   - Adds emotion extraction (GoEmotionDetector)
   - Computes perspective (certainty, polarity, sentiment) from linguistic cues
   - Negation, certainty, and sentiment word lists guide perspective values

3. **Graph Population** (`populate_ekg.py`):
   - Imports `LongTermMemory` from cltl.brain
   - Creates context first via `brain.capsule_context(context_capsule)`
   - Adds statements/events via `brain.capsule_event(capsule, reason_types=True)`

## Project-Specific Conventions

### URI Naming Scheme
- Base: `http://cltl.nl/leolani/`
- Entities: `world/{entity-name}` 
- Relations: `n2mu/{relation-name}` (n2mu = noun-to-modalized-utterance)
- Always use lowercase with hyphens for multi-word names

### Perspective Values
- **certainty**: 1 (certain) / 0 (uncertain) - detected from linguistic markers
- **polarity**: 1 (positive), -1 (negative), 0 (neutral)
- **sentiment**: 1 (positive), -1 (negative), 0 (neutral)
- **emotion**: list of emotion strings from GoEmotionDetector, or 0 if none

### File Organization
- `src/cltl/`: Core extraction logic (llm_event_triples*.py, events_to_capsules.py)
- `data/`: Raw conversations, extracted JSON/pickle, ontologies
- `data/openai_chatgpt_modelling/`: Ontology files (.ttl), T-box/A-box examples
- `doc/`: Architecture docs (populate_ekg.md, srl_statistics.md)

## Integration Points

### External Dependencies
- **cltl.brain**: Query/modify RDF graph via `LongTermMemory` class
- **cltl.commons.discrete**: UtteranceType enum (STATEMENT, EXPERIENCE, QUESTION)
- **cltl.commons.casefolding**: Text normalization for entity linking
- **OpenAI API**: LLM calls require key in path (currently hardcoded - see line 9 in llm_event_triples_openai.py)

### GraphDB Backend
- Running instance required at `http://localhost:7200/repositories/sandbox`
- Examples show `brain = LongTermMemory(address="http://localhost:7200/repositories/sandbox")`
- Query/store operations are async-safe but GraphDB must be up

## Essential Workflows

### Run Event Extraction
```bash
cd src/cltl
python -c "from llm_event_triples_openai import LLM_EventExtraction; 
extractor = LLM_EventExtraction(); 
annotations = extractor.annotate_all_turns_in_conversation(conversation)"
```

### Run Brain Examples (from cltl-knowledgerepresentation)
```bash
cd examples && python basic.py --logs ./log_output
python event_statements.py --logs ./log_output
```

### Generate Statistics
```python
from srl_statistics import get_statistics
stats = get_statistics(annotated_conversations, threshold=3)
```

## Common Patterns to Recognize

1. **List/String Normalization**: SRL slots like `agent`, `patient` can be string or list - code checks type and converts
2. **Sliding Window Processing**: Conversations processed turn-by-turn with context maintained
3. **Pickle + JSON Dual Storage**: LLM results saved twice for caching and analysis
4. **URI Generation**: Entity labels converted to URIs during capsule creation
5. **Emotion Extraction**: Done at capsule creation via GoEmotionDetector model (multilingual)

## Debugging Tips

- **LLM API failures**: Check OpenAI key path (line 9 of llm_event_triples_openai.py)
- **GraphDB failures**: Verify instance running at localhost:7200
- **Capsule format errors**: Validate against baking.json structure - all required fields must present
- **Perspective NaN**: Emotion detector may return empty list - code prunes "neutral" emotion
- **Missing URIs**: Check that entities have both `label` and `uri` fields in capsules

## Related Documentation

- `doc/llm_event_triples_openai.md`: Pydantic schema details
- `doc/populate_ekg.md`: Knowledge graph population walkthrough
- `data/openai_chatgpt_modelling/README.md`: T-box/A-box ontology examples

