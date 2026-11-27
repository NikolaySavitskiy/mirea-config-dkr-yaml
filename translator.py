"""Translate the variant 20 configuration language to YAML."""
import argparse
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
import re
import sys

TOKEN = re.compile(r"\s+|(?P<number>[+-]?\d+\.\d+)|(?P<name>[A-Z]+)|(?P<var>var\b)|(?P<symbol>\^\[|[{}\].])")


class SyntaxProblem(ValueError):
    pass


@dataclass(frozen=True)
class Token:
    kind: str
    text: str
    start: int


def tokenize(source):
    position = 0
    while position < len(source):
        match = TOKEN.match(source,position)
        if match is None:
            raise problem(source,position,f"Unexpected character {source[position]!r}")
        if match.lastgroup:
            yield Token(match.lastgroup,match.group(),position)
        position = match.end()
    yield Token("eof","",position)


def problem(source,position,message):
    line = source.count("\n",0,position)+1
    column = position-source.rfind("\n",0,position)
    return SyntaxProblem(f"{line}:{column}: {message}")


class Parser:
    def __init__(self, source):
        self.source = source
        self.stream = iter(tokenize(source))
        self.current = next(self.stream)
        self.constants = {}

    def take(self, expected):
        token = self.current
        if expected not in {token.text,token.kind}:
            raise problem(self.source,token.start,f"Expected {expected}, got {token.text!r}")
        self.current = next(self.stream)
        return token

    def value(self,depth=0):
        token = self.current
        if depth>128:
            raise problem(self.source,token.start,"Array nesting exceeds 128 levels")
        if token.kind == "number":
            return Decimal(self.take("number").text)
        if token.text == "^[":
            self.take("^[")
            name = self.take("name")
            self.take("]")
            if name.text not in self.constants:
                raise problem(self.source,name.start,f"Unknown constant {name.text}")
            return self.constants[name.text]
        if token.text == "{":
            self.take("{")
            values = []
            while self.current.text != "}":
                values.append(self.value(depth+1))
                self.take(".")
            self.take("}")
            return values
        raise problem(self.source,token.start,"Expected a number, array or constant reference")

    def parse(self):
        result = []
        while self.current.kind != "eof":
            if self.current.kind == "var":
                self.take("var")
                name = self.take("name")
                if name.text in self.constants:
                    raise problem(self.source,name.start,f"Duplicate constant {name.text}")
                self.constants[name.text] = self.value()
            else:
                result.append(self.value())
        if not result:
            return None
        return result[0] if len(result)==1 else result


def yaml_flow(value):
    if value is None:
        return "null"
    if isinstance(value,list):
        return "["+", ".join(map(yaml_flow,value))+"]"
    return format(value,"f")


def translate(source):
    return yaml_flow(Parser(source).parse())+"\n"


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--input",required=True,type=Path)
    args = cli.parse_args()
    try:
        sys.stdout.write(translate(args.input.read_text(encoding="utf-8-sig")))
    except (OSError,ValueError) as error:
        print(error,file=sys.stderr)
        return 1
    return 0


if __name__=="__main__":
    raise SystemExit(main())
