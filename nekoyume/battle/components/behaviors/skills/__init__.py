import math

from nekoyume.battle import WeightedList
from nekoyume.battle.components.bag import Bag
from nekoyume.battle.components.behaviors import Behavior
from nekoyume.battle.components.behaviors import BehaviorTreeStatus
from nekoyume.battle.components.behaviors.aggro import Aggro
from nekoyume.battle.components.stats import Stats
from nekoyume.battle.enums import AttackType, CharacterType, ItemType
from nekoyume.battle.status.skills import Attack as StatusAttack
from nekoyume.battle.status.skills import Casting, Delaying
from nekoyume.battle.status.skills import Heal as StatusHeal
from nekoyume.battle.status.skills import Taunt as StatusTaunt
from nekoyume.battle.status.stats import Dead, GetExp
from nekoyume.tables import Tables


class Skill(Behavior):
    subclasses = {}

    def __init_subclass__(cls):
        super().__init_subclass__()
        Skill.subclasses[cls.__name__] = cls

    def __init__(self, name):
        self.name = name
        self.data = Tables.skills[name]
        self.nexttime = self.data.cooltime
        self.is_casting = False
        self.cast_remains = 0

    def tick(self, simulator):
        pass

    # todo: is_dead check to filter
    def find_targets(self, simulator, filter_type):
        if not self.data.target_count:
            return []
        weightedlist = WeightedList()
        for target in simulator.characters:
            stats = target.get_component(Stats)
            aggro = target.get_component(Aggro)
            if filter_type == target.type_\
               and not stats.is_dead():
                weightedlist.add(target, aggro.value)
        if len(weightedlist) == 0:
            return []
        targets = []
        while len(targets) < self.data.target_count:
            targets.append(weightedlist.pop(simulator.random))
            if len(weightedlist) == 0:
                break
        return targets

    def calc_atk(self):
        my_stats = self.owner.get_component(Stats)
        my_bag = self.owner.get_component(Bag)
        weapon = my_bag.get_equipped(ItemType.WEAPON)
        atk = 0
        if weapon:
            atk = weapon.get_atk()
            if weapon.atk_type == AttackType.MELEE:
                atk += my_stats.calc_melee_atk()
            elif weapon.atk_type == AttackType.RANGED:
                atk += my_stats.calc_ranged_atk()
            elif weapon.atk_type == AttackType.MAGIC:
                atk += my_stats.calc_magic_atk()
        else:
            atk += my_stats.calc_melee_atk()
        atk = math.floor(atk * (self.data.power * 0.01))
        return atk

    def is_cooltime(self, simulator):
        return self.nexttime > simulator.time

    def kill(self, simulator, target):
        my_stats = self.owner.get_component(Stats)
        target_stats = target.get_component(Stats)
        simulator.logger.log(Dead(id_=target.id_))
        if self.owner.type_ is CharacterType.PLAYER:
            my_stats.get_exp(target_stats.data.reward_exp)
            simulator.logger.log(GetExp(
                id_=self.owner.id_,
                exp=target_stats.data.reward_exp
            ))

    def casting(self, simulator):
        my_stats = self.owner.get_component(Stats)
        if self.cast_remains > 0:
            if my_stats.check_damaged():
                # self.cast_remains += 1
                simulator.logger.log(Delaying(
                    id_=self.owner.id_,
                    tick_remain=self.cast_remains,
                ))
                # return True
            self.cast_remains -= 1
            simulator.logger.log(Casting(
                id_=self.owner.id_,
                tick_remain=self.cast_remains,
            ))
            return True
        if not self.is_casting and self.data.cast_time > 0:
            self.is_casting = True
            self.cast_remains = self.data.cast_time
            simulator.logger.log(Casting(
                id_=self.owner.id_,
                tick_remain=self.cast_remains,
            ))
            return True
        return False


# weapon based attack
class Attack(Skill):
    def tick(self, simulator):
        if self.is_cooltime(simulator):
            return BehaviorTreeStatus.FAILURE
        my_stats = self.owner.get_component(Stats)
        atk = self.calc_atk()
        target_type = my_stats.get_target_type()
        targets = self.find_targets(simulator, target_type)
        for index, target in enumerate(targets):
            target_stats = target.get_component(Stats)
            damaged = target_stats.damaged(atk)
            target_aggro = target.get_component(Aggro)
            target_aggro.add(self.owner.id_, 1)
            simulator.logger.log(StatusAttack(
                id_=self.owner.id_,
                value=damaged,
                target_id=target.id_,
                target_hp=target_stats.hp,
                target_remain=len(targets) - index - 1,
            ))
            if target_stats.is_dead():
                self.kill(simulator, target)
        return BehaviorTreeStatus.SUCCESS


class Spell(Skill):
    def tick(self, simulator):
        if self.is_cooltime(simulator):
            return BehaviorTreeStatus.FAILURE
        if self.casting(simulator):
            return BehaviorTreeStatus.SUCCESS
        my_aggro = self.owner.get_component(Aggro)
        my_aggro.value += 1
        my_stats = self.owner.get_component(Stats)
        self.nexttime += my_stats.calc_cooltime(self.data.cooltime)
        self.is_casting = False
        atk = math.floor(my_stats.calc_magic_atk() * (self.data.power * 0.01))
        target_type = my_stats.get_target_type()
        targets = self.find_targets(simulator, target_type)
        for index, target in enumerate(targets):
            target_stats = target.get_component(Stats)
            damaged = target_stats.damaged(atk)
            target_aggro = target.get_component(Aggro)
            target_aggro.add(self.owner.id_, 1)

            simulator.logger.log(StatusAttack(
                id_=self.owner.id_,
                value=damaged,
                target_id=target.id_,
                target_hp=target_stats.hp,
                target_remain=len(targets) - index - 1,
            ))
            if target_stats.is_dead():
                self.kill(simulator, target)
        return BehaviorTreeStatus.SUCCESS


class Heal(Skill):
    def tick(self, simulator):
        if self.is_cooltime(simulator):
            return BehaviorTreeStatus.FAILURE
        if self.casting(simulator):
            return BehaviorTreeStatus.SUCCESS
        my_aggro = self.owner.get_component(Aggro)
        my_aggro.value += 1
        my_stats = self.owner.get_component(Stats)
        self.nexttime += my_stats.calc_cooltime(self.data.cooltime)
        targets = self.find_targets(simulator, self.owner.type_)
        for index, target in enumerate(targets):
            target_stats = target.get_component(Stats)
            if target_stats:
                amount = math.floor(
                    my_stats.calc_magic_atk() * (self.data.power * 0.01))
                target_stats.heal(amount)
                simulator.logger.log(StatusHeal(
                    id_=self.owner.id_,
                    value=amount,
                    target_id=target.id_,
                    target_hp=target_stats.hp,
                    target_remain=len(targets) - index - 1,
                ))
        return BehaviorTreeStatus.SUCCESS


class Slow(Skill):
    def tick(self, simulator):
        # TODO
        return BehaviorTreeStatus.FAILURE


class Taunt(Skill):
    def tick(self, simulator):
        if self.is_cooltime(simulator):
            return BehaviorTreeStatus.FAILURE
        my_aggro = self.owner.get_component(Aggro)
        my_aggro.value += math.floor(self.data.power * 0.01)
        my_stats = self.owner.get_component(Stats)
        self.nexttime += my_stats.calc_cooltime(self.data.cooltime)
        simulator.logger.log(StatusTaunt(id_=self.owner.id_))
        return BehaviorTreeStatus.SUCCESS
