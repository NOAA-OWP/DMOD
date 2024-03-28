"""
@TODO: Put a module wide description here
"""
from __future__ import annotations

import pydantic
from typing_extensions import Self
from unittest import TestCase
import typing

from ....core.common import types


class TestEnum(types.CommonEnum):
    @classmethod
    def default(cls) -> Self:
        return cls.VALUE_ONE

    VALUE_ONE = "one"
    VALUE_TWO = "two"
    VALUE_THREE = "three"


class EnumContainer(pydantic.BaseModel):
    enum_member: TestEnum


class TestTypes(TestCase):
    def test_commonenum(self):
        container_one = EnumContainer(enum_member=TestEnum.VALUE_ONE)
        container_two = EnumContainer(enum_member="one")
        container_three = EnumContainer(enum_member="oNe")

        self.assertEqual(TestEnum.VALUE_ONE, "one")
        self.assertEqual(TestEnum.VALUE_ONE, container_one.enum_member)
        self.assertEqual(TestEnum.VALUE_ONE, container_two.enum_member)
        self.assertEqual(TestEnum.VALUE_ONE, container_three.enum_member)
