from pydantic import BaseModel
from typing_extensions import Self

from pydantic_init import FromInitMixin


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
