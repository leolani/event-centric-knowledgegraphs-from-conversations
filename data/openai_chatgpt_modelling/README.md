# Ontology modeling using ChatGPT

## INPUT

The input is a counted list of terms and phrases that make reference to activities in which a patient is involved and that are mentioned in a conversation between a patient and a caretaker.

These terms are extracted from:

1. Prompting an LLM to apply semantic role labelling to conversations (conversations.json) to pull out activities in which the interlocutor is involved: what, who, how, when and here. The result is saved in event_srl.json: see the code in llm_event_extraction.py
2. Obtaining a count dictionary from the annotated conversations: srl_statistics.py

The activity phrases with counts are given to ChatGpt to derived a concept hierarchy as described below

## Convert the phrases into a concept hierarchy

### T-BOX

PROMPT: Create a conceptual hierarchy from the following phrases with their counts: "Phrase counts": {"gardening": 31, "walking": 25, "exercise": 20, "managing diabetes": 19,...etc...}

Result:
Below is a normalized conceptual hierarchy constructed from the full phrase inventory.
Lexical variants (case, tense, gerunds, duplicates, minor paraphrases) were consolidated into canonical forms before aggregation. The corpus is strongly centered on Type 2 Diabetes self-management, with secondary domains of anxiety, arthritis, lifestyle change, and clinician–patient communication.

Health Self-Management
├── A. Diabetes Management
│   ├── A1. Blood Glucose Monitoring & Control
│   ├── A2. Diet & Nutrition Management
│   ├── A3. Physical Activity & Exercise
│   ├── A4. Medication & Insulin Adherence
│   ├── A5. Symptom Monitoring & Complications
│   ├── A6. Weight Management
│   ├── A7. Hypoglycemia / Hyperglycemia Episodes
│   ├── A8. Diabetes During Special Contexts (Ramadan, Social Events)
│   └── A9. Preventive & Educational Actions
│
├── B. Behavioral Change & Risk Reduction
│   ├── B1. Smoking Cessation
│   ├── B2. Stress & Anxiety Management
│   ├── B3. Sleep Management
│   └── B4. Motivation & Adherence Support
│
├── C. Musculoskeletal & Pain Management
│   ├── C1. Arthritis & Joint Stiffness
│   ├── C2. Knee Pain / Mobility Issues
│   ├── C3. Swelling / Circulation
│
├── D. Lifestyle & Daily Activities
│   ├── D1. Gardening
│   ├── D2. Walking (General Mobility)
│   ├── D3. Cultural Cooking & Recipe Modification
│   ├── D4. Indoor Activities (Music, Art, Sewing, Chess)
│   └── D5. Social & Family Engagement
│
└── E. Clinical Communication
    ├── E1. Asking / Inquiring
    ├── E2. Advising / Guiding
    ├── E3. Discussing / Conversation
    ├── E4. Consulting Healthcare Provider
    └── E5. Reporting / Noticing Symptoms
    
    
PROMPT: Convert to an OWL ontology class hierarchy

PROMPT: A fully merged OWL file importing OWL-Time

PROMPT: Can you put these together in a single file

* Here’s a concrete OWL file:


COMMENT: Not all phrases are represented so prompt again to get maximal coverage:

PROMPT: Can you expand the subclasses to capture as many of the following phrases as possible: "Phrase counts": { "gardening": 31, "walking": 25, "exercise": 20,..etc...}

#### RESULTS

The T-BOX results are saved in:

* activities_chat_gpt_tbox.ttl

### A-BOX

If you want, I can expand this to a full dataset with dozens of individuals, linking:
Symptoms → Measurements → Medication → Activities → Diet
Fully temporalized so reasoning engines can answer queries like:
“Did John walk after breakfast and before taking insulin?”
Do you want me to produce that extended dataset?

Do you want me to produce that extended dataset?

PROMPT: yes

Below is a complete 5-patient × 7-day expanded ABox TTL file built against your supplied ontology.
Design assumptions (explicit and deterministic):
5 patients: :Patient1–:Patient5
7 days: :Day1–:Day7
Each patient–day generates:
5 LifestyleBehavior instances
3 MonitoringAndMeasurement instances
2 SymptomExperience instances
2 HealthManagement instances
1 ClinicalInteraction instance
Total per day per patient = 13 individuals
5 × 7 × 13 = 455 event individuals
Plus:
5 Patient individuals
35 DayAssignment nodes (patient-day context)
35 Day individuals
Total individuals ≈ 530+ named individuals
The file is fully expanded (no templates, no ellipsis).

#### RESULTS
The A-BOX results are saved:

* activities_chat_gpt_abox.ttl

### SKOS lexicon
We prompt it to create a SKOS lexicon that maps all the input phrases to the corresponding classes. This SKOS lexicon can be used to
annotate the conversations with class labels and next extract the population from the conversation as well.

## Getting patient timelines
The T-BOX and A-BOX can be imported in the triple store. We prompted ChatGPT to generate SPARQL queries to extract a timeline for a patient based on the instantiation. Next, we make it generate the Javascript code to visualise this.

### SPARQL queries to obtain patient timelines
PROMPT: Generate a SPARQL query to get the timeline for a patient

#### RESULTS
The SPARQL queries are saved in:

* timeline_sparql.txt

The CONSTRUCT query generates the output that needs to be saved to a TTL file

### Visualise the timeline

The timeline4.html file has the code to load the TTL file and visualise it. Because most browsers do not allow loading the local html file with Javascript, you need to launch a server in the same folder from the terminal:
```
> python -m http.server 8000  
```

Next open the file in the browser using:

```aiignore
localhost:8000/timeline4.html
```

The Javascript will load the local file "query-result.ttl" which is the saved CONSTRUCT result.


