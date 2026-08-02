from dataclasses import dataclass


@dataclass
class RecipeChannel:
    channel_id: int
    enabled: bool
    method: str | None
    units: str | None
    amount: int | None


@dataclass
class Recipe:
    recipe_id: int
    channels: list[RecipeChannel]