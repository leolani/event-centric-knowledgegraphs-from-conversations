# SRL Annotation Tool

A browser-based tool for manually annotating semantic roles in conversation data. Annotations follow the output format of `events_srl_typed.json` and can be saved and reloaded across sessions.

## Requirements

No installation required. Open `annotation_tool.html` in any modern web browser (Chrome, Firefox, Safari, Edge).

## Getting started

1. Open `annotation_tool.html` in your browser.
2. Click **Load conversations.json** and select `data/conversations.json`.
3. Select a conversation from the sidebar.
4. Annotate turns (see workflow below).
5. Click **Export JSON** to save your work.

You can load in either order: if you load an annotations file before `conversations.json`, the tool queues it and applies it automatically once the conversations are loaded.

## Interface overview

```
┌─────────────────────────────────────────────────────┐
│  Annotator: [piek]  [Load conversations.json]        │
│  [Load Existing Annotations]  [Export JSON]          │
├──────────────┬──────────────────────────────────────┤
│ CONVERSATIONS│  Chat 0 — Jan — 2013,Apr,13           │
│              │  ┌─────────────────────────────────┐  │
│ Chat 0  [3]  │  │ Turn 1  agent                   │  │
│ Chat 1       │  │ Hey Jan, I see that you're a... │  │
│ Chat 2       │  │ [chat0.1] cycling [exercise]    │  │
│  ...         │  │  agent: Jan(person)  time: ...  │  │
│              │  │  + Add Activity Annotation      │  │
│              │  └─────────────────────────────────┘  │
└──────────────┴──────────────────────────────────────┘
```

The sidebar lists all conversations with a badge showing how many annotation entries have been made. Use the filter box at the top of the sidebar to search by human name, date, or chat number.

## Annotation workflow

### Step 1 — Add an activity annotation to a turn

Click **+ Add Activity Annotation** below any turn. A modal opens with two options:

**New activity**
- *Activity*: the word or phrase that names the activity (e.g. `cycling`). You can type it or pre-fill it by selecting text in the utterance (see below).
- *Activity type*: choose from the dropdown (see [Activity types](#activity-types)).
- *Activity ID*: auto-generated as `chat{N}.{M}` (e.g. `chat0.1`). Edit if needed. Must be unique within a conversation.

**Reference previous activity**
- Appears only when activities have already been defined in earlier turns of the same conversation.
- Select an existing activity ID from the dropdown. The annotation records additional role information for that activity without repeating the activity name and type.

### Step 2 — Assign roles

There are two ways to add role values to an annotation entry.

**By selecting text in the utterance (fastest)**

1. Click and drag to select a word or phrase in the utterance text.
2. A small popup appears with:
   - **✦ Use as new activity name** — pre-fills the activity field and opens the new annotation modal.
   - Annotation selector (which annotation entry to attach the role to).
   - Role radio buttons.
   - Type dropdown (options depend on the role chosen).
3. Click **Assign Role**.

**Via the + Role button**

Click **+ Role** on any annotation card. A modal shows the full utterance text for reference. Type or paste the phrase, select the role, and choose the type.

### Step 3 — Add time resolution (optional)

Click **+ Time Resolved** on any annotation card to ground a time expression to calendar dates:

| Field | Example |
|---|---|
| Time expression | `recently`, `last week`, `lately` |
| Temporal type | `point`, `range`, `duration`, `recurring`, `vague` |
| Absolute date | `2013-04-13` |
| Date range start | `2013-04-01` |
| Date range end | `2013-04-13` |
| Recurrence pattern | `daily`, `regularly`, `often`, `now-and-then`, `sometimes`, `rarely` |

### Editing and deleting

- Click **Edit Activity** on a card to change the activity name, type, or ID.
- Click **×** next to any role value, time expression, or time resolution to remove it.
- Click **Delete** on a card to remove the entire annotation entry.

### Step 4 — Annotate the speaker's perspective

Each turn header has three dropdowns next to the speaker badge, capturing the speaker's perspective on their utterance. All three are exported together as a single `perspective` object on each Output entry for the turn (see [Output format](#output-format)).

| Dropdown | Values | Default |
|---|---|---|
| **speaker emotion** | The 28 Google GoEmotions classes (see `src/cltl/emotion_classes.py`). `neutral` is pinned at the top; the rest are grouped into **Positive**, **Negative**, and **Ambiguous** (`surprise`, `realization`), each sorted alphabetically. | `neutral` |
| **speaker certainty** | `certain`, `uncertain`, `neutral` | `neutral` |
| **speaker factuality** | `confirm`, `deny`, `expect` | `confirm` |

Select the values that best describe the speaker's emotion, certainty, and factuality (confirming, denying, or merely expecting the activity) for that utterance.

## Semantic roles

Each annotation entry can carry the following roles. All roles except `time` take a **value** (the phrase) and a **type** (from the dropdown).

| Role | Description | Types |
|---|---|---|
| `agent` | Who or what performs the activity | person, group, organization, object, substance, vehicle, tool, place, city, country, indoor, outdoor, other |
| `patient` | What the activity acts upon | same as agent |
| `instrument` | Tool or means used | same as agent |
| `manner` | How the activity is performed | same as agent |
| `location` | Where the activity takes place | same as agent |
| `result` | Outcome or purpose of the activity | **goal**, **impact** |
| `time` | When the activity occurs (free text phrase) | — |

## Activity types

The activity type dropdown contains the types found in `events_srl_typed.json`:

`advise` · `diet` · `disease` · `exercise` · `measurement` · `medicine` · `mental condition` · `physical condition` · `social` · `social condition` · `symptom` · `take_drink` · `take_food` · `treatment` · `other`

## Output format

**Export JSON** saves a file named `annotations_<annotator>.json`. The structure is an array of conversations, each being an array of annotated turns.
An example of the structure can be found in ```annotations.json```.

Turns with no annotations are omitted from the export. A **reference entry** (second turn above) has `activity_id` but no `activity` or `activity_type` fields — it links additional role information to an activity defined in an earlier turn.

Every Output entry carries a `perspective` object with the turn's speaker-perspective annotations (see [Step 4](#step-4--annotate-the-speakers-perspective)):

```json
{ "perspective": { "emotion": "neutral", "factuality": "confirm", "certainty": "neutral" } }
```

Since these three dropdowns apply to the whole turn, every Output entry for the same turn is exported with the same `perspective` values.

## Tips

- The activity ID badge (dark chip) on each annotation card shows which activity it belongs to, making it easy to track an activity across multiple turns.
- The sidebar badge count updates as you annotate so you can see which conversations have been started.
- You can filter the conversation list with the search box — it matches on human name, date, or chat number.
- Save frequently using **Export JSON**. Reload your work via **Load Existing Annotations** (before or after loading `conversations.json`).
