from .base import BaseModel


class Control(BaseModel):
    id: int
    name: str
    control: dict


class ControlSet(BaseModel):
    id: int
    name: str
    controls: list[Control]


class Policy(BaseModel):
    id: int
    name: str
    control_sets: list[ControlSet]
