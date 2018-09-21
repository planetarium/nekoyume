from dataclasses import dataclass

from nekoyume.battle.status.base import Status


@dataclass
class GetItem(Status):
    type: str = 'get_item'
    id_: str = ''
    item: str = ''
