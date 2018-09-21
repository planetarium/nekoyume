from dataclasses import dataclass

from nekoyume.battle.status.base import Status


@dataclass
class Dead(Status):
    type: str = 'dead'
    id_: str = ''


@dataclass
class GetExp(Status):
    type: str = 'get_exp'
    id_: str = ''
    exp: int = 0
