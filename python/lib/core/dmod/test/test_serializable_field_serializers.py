import unittest
from typing import List
from pydantic import SecretStr
from datetime import date

from ..core.serializable import Serializable


class Country(Serializable):
    name: str
    phone_code: int

    class Config:
        field_serializers = {"name": lambda s: s.upper()}


class Address(Serializable):
    post_code: int
    country: Country


class CardDetails(Serializable):
    number: SecretStr
    expires: date


class Hobby(Serializable):
    name: str
    info: str

    class Config:
        fields = {"name": {"alias": "NAME"}}


class User(Serializable):
    first_name: str
    second_name: str
    address: Address
    card_details: CardDetails
    hobbies: List[Hobby]

    class Config:
        field_serializers = {"first_name": lambda f: f.upper()}


class A(Serializable):
    field: str

    class Config:
        field_serializers = {"field": lambda s: s.lower()}


class B(Serializable):
    field: str

    class Config:
        field_serializers = {"field": lambda s: s.upper()}


class C(Serializable):
    a: A
    b: B


class D(Serializable):
    field: str

    class Config:
        field_serializers = {"field": lambda s: s.upper()}


class E(D):
    class Config:
        field_serializers = {"field": lambda s: s}


class F(Serializable):
    a: str

    class Config:
        field_serializers = {"a": lambda s: s.lower()}


class G(Serializable):
    b: str

    class Config:
        field_serializers = {"b": lambda s: s.upper()}


class H(F, G):
    ...


class I(G, F):
    ...


class J(Serializable):
    a: int


class K(Serializable):
    j: J

    class Config:
        field_serializers = {"j": lambda self, _: self.j.a}


class L(Serializable):
    a: str

    class Config:
        field_serializers = {"a": 12}


class M(Serializable):
    a: str

    class Config:
        field_serializers = {"a": lambda a, b, c: (a, b, c)}


class N(Serializable):
    a: str

    class Config:
        field_serializers = {"a": lambda: "should fail"}


class RootModel(Serializable):
    __root__: int

    class Config:
        field_serializers = {"__root__": lambda s: s ** 2}


def user_fixture() -> User:
    return User(
        first_name="John",
        second_name="Doe",
        address=Address(post_code=123456, country=Country(name="usa", phone_code=1)),
        card_details=CardDetails(number=4212934504460000, expires=date(2020, 5, 1)),
        hobbies=[
            Hobby(name="Programming", info="Writing code and stuff"),
            Hobby(name="Gaming", info="Hell Yeah!!!"),
        ],
    )


class TestFieldSerializerConfigOption(unittest.TestCase):
    def test_exclude_keys_User(self):
        user = user_fixture()

        exclude_keys = {
            "second_name": True,
            "address": {"post_code": True, "country": {"phone_code"}},
            "card_details": True,
            # You can exclude fields from specific members of a tuple/list by index:
            "hobbies": {-1: {"info"}},
        }

        expect = {
            "first_name": "JOHN",
            "address": {"country": {"name": "USA"}},
            "hobbies": [
                {
                    "name": "Programming",
                    "info": "Writing code and stuff",
                },
                {"name": "Gaming"},
            ],
        }

        self.assertDictEqual(user.dict(exclude=exclude_keys), expect)

    def test_include_keys_User(self):
        user = user_fixture()

        include_keys = {
            "first_name": True,
            "address": {"country": {"name"}},
            "hobbies": {0: True, -1: {"name"}},
        }

        expect = {
            "first_name": "JOHN",
            "address": {"country": {"name": "USA"}},
            "hobbies": [
                {
                    "name": "Programming",
                    "info": "Writing code and stuff",
                },
                {"name": "Gaming"},
            ],
        }

        self.assertDictEqual(user.dict(include=include_keys), expect)

    def test_exclude_keys_by_alias_User(self):
        user = user_fixture()

        exclude_keys = {
            "second_name": True,
            "address": {"post_code": True, "country": {"phone_code"}},
            "card_details": True,
            # You can exclude fields from specific members of a tuple/list by index:
            "hobbies": {-1: {"info"}},
        }

        expect = {
            "first_name": "JOHN",
            "address": {"country": {"name": "USA"}},
            "hobbies": [
                {
                    "NAME": "Programming",
                    "info": "Writing code and stuff",
                },
                {"NAME": "Gaming"},
            ],
        }

        self.assertDictEqual(user.dict(exclude=exclude_keys, by_alias=True), expect)

    def test_composed_fields_dont_mangle_C(self):
        o = C(a=A(field="A"), b=B(field="b"))

        expect = {"a": {"field": "a"}, "b": {"field": "B"}}
        self.assertDictEqual(o.dict(), expect)

    def test_override_in_subclass_D_E(self):
        o = D(field="a")
        self.assertEqual(o.dict()["field"], "A")

        subclass_o = E(field="a")

        self.assertEqual(subclass_o.dict()["field"], "a")

    def test_root_model_RootModel(self):
        o = RootModel(__root__=12)
        self.assertEqual(o.dict()["__root__"], 144)

    def test_multi_inheritance_H_I(self):
        # H(F, G)
        h = H(a="a", b="b")
        # I(G, H)
        i = I(a="a", b="b")

        expect = {
            "a": "a",
            "b": "B",
        }

        self.assertDictEqual(h.dict(), expect)
        self.assertDictEqual(i.dict(), expect)

    def test_pull_up_K(self):
        o = K(j=J(a=12))

        expect = {"j": 12}

        self.assertDictEqual(o.dict(), expect)

    def test_raises_value_error_L(self):
        o = L(a="a")
        with self.assertRaises(ValueError):
            o.dict()

    def test_raises_runtime_error_too_many_params_M(self):
        o = M(a="a")

        with self.assertRaises(RuntimeError):
            o.dict()

    def test_raises_runtime_error_too_few_params_N(self):
        o = N(a="a")

        with self.assertRaises(RuntimeError):
            o.dict()

    def test_fixes_380(self):
        class Model(Serializable):
            field: int

            class Config(Serializable.Config):
                field_serializers = {"field": str}

        m = Model(field=42)
        self.assertDictEqual(m.dict(), {"field": "42"})
