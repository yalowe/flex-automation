from dataclasses import dataclass

@dataclass
class CommandResult:
    command: str
    success: bool
    response: str
