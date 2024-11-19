import pathlib

import pydantic
import pytest
import yaml

import tlsh


class HashingCase(pydantic.BaseModel):
    input: str
    output: str


class Cases(pydantic.BaseModel):
    hashing: list[HashingCase]

    @classmethod
    def fromYaml(cls):

        with open(pathlib.Path(__file__).resolve().parent / "cases.yaml", "r") as file:
            data = yaml.safe_load(file)

        return cls.model_validate(data)


@pytest.fixture(scope="session")
def cases():
    return Cases.fromYaml()


def test_against_known_outputs(cases: Cases):

    for case in cases.hashing:
        assert tlsh.Tlsh.compute_hash(case.input) == case.output
