from dataclasses import dataclass, asdict


@dataclass
class Status:
    type: str = ''

    def __str__(self):
        return str(asdict(self))
