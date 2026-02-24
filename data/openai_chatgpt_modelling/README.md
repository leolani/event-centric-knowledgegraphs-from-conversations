# Ontology modeling using ChatGPT

## Input

The input is a list of terms and phrases that make reference to activities in which a patient is involved and that are mentioned in a conversation between a patient and a caretaker.


## Convert the phrases into a concept hiearchy

PROMPT: Create a conceptual hierarchy from the following phrases with their counts: "Phrase counts": {"gardening": 31, "walking": 25, "exercise": 20, "managing diabetes": 19,....}



Below is a normalized conceptual hierarchy constructed from the full phrase inventory.
Lexical variants (case, tense, gerunds, duplicates, minor paraphrases) were consolidated into canonical forms before aggregation.
The corpus is strongly centered on Type 2 Diabetes self-management, with secondary domains of anxiety, arthritis, lifestyle change, and clinician–patient communication.

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

PROMPT: A TBox + ABox instance dataset

Perfect. You want a full OWL ontology with a TBox (schema) plus an ABox (instances/data). I can create a merged RDF/XML file with:
TBox – the class hierarchy from your previous ontology.
ABox – example individuals for each main class, including relationships.
Here’s a concrete OWL file with both TBox and ABox:

If you want, I can expand this to a full dataset with dozens of individuals, linking:
Symptoms → Measurements → Medication → Activities → Diet
Fully temporalized so reasoning engines can answer queries like:
“Did John walk after breakfast and before taking insulin?”
Do you want me to produce that extended dataset?

Do you want me to produce that extended dataset?

PROMPT: yes

COMMENT: Not all phrases are represented so prompt again for all:

PROMPT: Can you expand the subclasses to capture as many of the following phrases as possible: "Phrase counts": { "gardening": 31, "walking": 25, "exercise": 20,..etc...}

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

PROMPT: Generate a SPARQL query to get the timeline for a patient

