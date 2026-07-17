"""
Closed vocabularies shared by the LLM extraction prompt (prompts.py), the Pydantic
models (llm_event_triples_openai_pydantic.py) and the annotation tool's dropdowns
(src/cltl/annotation/annotation_tool.html, via generate_dropdown_values.py). Keeping
these enums in one place means the prompt, the code and the tool can never drift
out of sync — change a value here and regenerate dropdown_values.js.
"""

from enum import Enum


class ActivityType(str, Enum):
        exercise = "exercise"
        measurement = "measurement"
        take_food = "take_food"
        take_drink = "take_drink"
        advise = "advise"
        social = "social"
        diet = "diet"
        treatment = "treatment"
        medicine = "medicine"
        physical_condition = "physical condition"
        social_condition = "social condition"
        mental_condition = "mental condition"
        symptom = "symptom"
        disease = "disease"
        other = "other"


class RoleType(str, Enum):
        person = "person"
        group = "group"
        organization = "organization"
        object = "object"
        substance = "substance"
        vehicle = "vehicle"
        tool = "tool"
        place = "place"
        city = "city"
        country = "country"
        indoor = "indoor"
        outdoor = "outdoor"
        other = "other"


class ResultType(str, Enum):
        goal = "goal"
        impact = "impact"


class EmotionLabel(str, Enum):
        admiration = "admiration"
        amusement = "amusement"
        anger = "anger"
        annoyance = "annoyance"
        approval = "approval"
        caring = "caring"
        confusion = "confusion"
        curiosity = "curiosity"
        desire = "desire"
        disappointment = "disappointment"
        disapproval = "disapproval"
        disgust = "disgust"
        embarrassment = "embarrassment"
        excitement = "excitement"
        fear = "fear"
        gratitude = "gratitude"
        grief = "grief"
        joy = "joy"
        love = "love"
        nervousness = "nervousness"
        optimism = "optimism"
        pride = "pride"
        realization = "realization"
        relief = "relief"
        remorse = "remorse"
        sadness = "sadness"
        surprise = "surprise"
        neutral = "neutral"


class Factuality(str, Enum):
        confirm = "confirm"
        deny = "deny"
        expect = "expect"


class Certainty(str, Enum):
        certain = "certain"
        uncertain = "uncertain"
        neutral = "neutral"


class TemporalType(str, Enum):
        point = "point"
        range = "range"
        duration = "duration"
        recurring = "recurring"
        vague = "vague"


class RecurrencePattern(str, Enum):
        daily = "daily"
        regularly = "regularly"
        often = "often"
        now_and_then = "now-and-then"
        sometimes = "sometimes"
        rarely = "rarely"


# The annotation tool's dropdowns (src/cltl/annotation/annotation_tool.html) group the 28
# EmotionLabel values by sentiment for display; this is the single source of truth for that
# grouping, shared by the annotation tool's generated dropdown_values.js (see
# src/cltl/annotation/generate_dropdown_values.py) and kept separate from "neutral", which is
# pinned as the default rather than shown in any group.
EMOTION_GROUPS = {
        "positive": [EmotionLabel.admiration, EmotionLabel.amusement, EmotionLabel.approval, EmotionLabel.caring,
                     EmotionLabel.curiosity, EmotionLabel.desire, EmotionLabel.excitement, EmotionLabel.gratitude,
                     EmotionLabel.joy, EmotionLabel.love, EmotionLabel.optimism, EmotionLabel.pride, EmotionLabel.relief],
        "negative": [EmotionLabel.anger, EmotionLabel.annoyance, EmotionLabel.confusion, EmotionLabel.disappointment,
                     EmotionLabel.disapproval, EmotionLabel.disgust, EmotionLabel.embarrassment, EmotionLabel.fear,
                     EmotionLabel.grief, EmotionLabel.nervousness, EmotionLabel.remorse, EmotionLabel.sadness],
        "ambiguous": [EmotionLabel.realization, EmotionLabel.surprise],
}

DEFAULT_EMOTION = EmotionLabel.neutral
DEFAULT_CERTAINTY = Certainty.neutral
DEFAULT_FACTUALITY = Factuality.confirm

# Role-type dropdown per role, matching the annotation tool's ROLE_TYPES map: "result" has its
# own closed vocabulary (no "other"), every other role uses the shared RoleType list.
ROLE_TYPES = {
        "default": list(RoleType),
        "result": list(ResultType),
}


def quoted_values(enum_cls) -> str:
        """Render an enum's values as a quoted, comma-separated list for embedding in prompt text."""
        return ", ".join(f'"{member.value}"' for member in enum_cls)