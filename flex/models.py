from dataclasses import dataclass


@dataclass
class Program:
    id: int
    active: bool
    units: str
    state: str
    error: str


@dataclass
class Shift:
    program_id: int
    recipe_id: int
    amount: int
    valves: int


@dataclass
class Recipe:
    id: int
    active: bool
    method: str
    units: str
    amount: int

@dataclass
class CommandResult:
    command: str
    success: bool
    response: str

@dataclass
class AlertConfig:
    name: str
    value: str
    delay_count: int
    active: bool
    action: str