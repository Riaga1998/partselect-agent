"""Core data schema for the PartSelect agent.

Everything the agent knows about flows through these models. Note that
`appliance_type` is just a field, not a hardcoded branch — that is what lets
us extend from "refrigerator + dishwasher" to any category by adding data,
not by rewriting logic.
"""
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class ApplianceType(str, Enum):
    refrigerator = "refrigerator"
    dishwasher = "dishwasher"


class Difficulty(str, Enum):
    easy = "Easy"
    moderate = "Moderate"
    hard = "Hard"


class Part(BaseModel):
    ps_number: str                                  # PartSelect id, e.g. "PS11752778"
    mfr_part_number: str                            # manufacturer part no, e.g. "WPW10321304"
    name: str
    brand: str
    appliance_type: ApplianceType
    category: str                                   # e.g. "Door Shelf Bin"
    price: float
    in_stock: bool = True
    description: str = ""
    compatible_brands: list[str] = Field(default_factory=list)
    compatible_models: list[str] = Field(default_factory=list)
    symptoms_fixed: list[str] = Field(default_factory=list)
    install_difficulty: Difficulty = Difficulty.easy
    install_time_mins: int = 15
    install_steps: list[str] = Field(default_factory=list)
    install_video_url: Optional[str] = None
    rating: float = 0.0
    review_count: int = 0
    related_parts: list[str] = Field(default_factory=list)
    image_url: Optional[str] = None
    product_url: Optional[str] = None


class ApplianceModel(BaseModel):
    model_number: str                               # e.g. "WDT780SAEM1"
    brand: str
    appliance_type: ApplianceType
    description: str = ""
    compatible_parts: list[str] = Field(default_factory=list)  # PS numbers
    common_symptoms: list[str] = Field(default_factory=list)


class CompatibilityResult(BaseModel):
    """Structured verdict so the frontend can render a ✓ / ✗ / ? badge."""
    compatible: Optional[bool]                      # True / False / None (unknown)
    part_number: str
    model_number: str
    reason: str
    part: Optional[Part] = None
