from dataclasses import dataclass


@dataclass
class DosingScenario:
    name: str
    program_id: int

    wait_time_sec: int | None = None