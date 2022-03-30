import typing

from . import specification

class Evaluator:
    def __init__(self, instructions: specification.EvaluationSpecification):
        self.__instructions = instructions
