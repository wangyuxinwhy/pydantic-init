from typing import List

from pydantic import BaseModel, TypeAdapter
from typing_extensions import Self

from pydantic_init import FromInitMixin, init


class Weapon(FromInitMixin):
    def __init__(self, name: str, damage: int) -> None:
        self.name = name
        self.damage = damage

    @classmethod
    def from_role(cls, role: str) -> Self:
        """Create a weapon based on the role.

        Args:
            role: The role of the hero. Only 'tank' is supported.
        """
        if role == 'tank':
            return cls('sword', 10)
        raise ValueError(f'Unknown role: {role}')

    def __str__(self) -> str:
        return f'{self.name} - {self.damage} damage'


class Hero(BaseModel):
    name: str
    weapon: Weapon


def test_from_init() -> None:
    weapon = Weapon.model_validate({'name': 'axe', 'damage': 15})
    assert str(weapon) == 'axe - 15 damage'

    weapon = Weapon.model_validate({'role': 'tank'})
    assert str(weapon) == 'sword - 10 damage'

    weapons = TypeAdapter(List[Weapon]).validate_python([{'name': 'axe', 'damage': 15}, {'role': 'tank'}])
    assert str(weapons[0]) == 'axe - 15 damage'
    assert str(weapons[1]) == 'sword - 10 damage'

    hero = Hero.model_validate({'name': 'Conan', 'weapon': {'name': 'axe', 'damage': 15}})
    assert hero.name == 'Conan'
    assert str(hero.weapon) == 'axe - 15 damage'


def test_init() -> None:
    weapon = init({'_component_': 'tests.test_init.Weapon', 'name': 'axe', 'damage': 15})
    assert str(weapon) == 'axe - 15 damage'

    weapon = init({'_component_': 'tests.test_init.Weapon', 'role': 'tank'})
    assert str(weapon) == 'sword - 10 damage'

    counter = init({'_component_': 'collections.Counter', '_args_': ['abb']})
    assert counter.most_common(1) == [('b', 2)]

    date = init({'_component_': 'datetime.date', 'year': 2021, 'month': 1, 'day': 1})
    assert date.isoformat() == '2021-01-01'

    date = init({'_component_': 'datetime.date.fromisocalendar', 'year': 2021, 'week': 1, 'day': 1})
    assert date.isoformat() == '2021-01-04'
