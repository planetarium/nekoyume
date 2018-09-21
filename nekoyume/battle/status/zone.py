from dataclasses import dataclass

from nekoyume.battle.status.base import Status


@dataclass
class Zone(Status):
    type: str = 'zone'
    id_: str = ''
