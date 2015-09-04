#! /usr/bin/env python3
from re import compile


re_not = compile("([\W])[!~]")
re_and = compile(",")
sire_not = compile("([\W])not_")
sire_and = compile("_and_")


def to_regex(siregex: str) -> str:
    """
    Transforms a signal regex into an ordinary regex understood by GOAL.
    """
    regex = re_not.sub("\\1not_", siregex)
    regex = re_and.sub("_and_", regex)
    return regex


def from_regex(regex: str) -> str:
    """
    Transforms a modified GOAL regex back into signal regex.
    """
    siregex = sire_and.sub(",", regex)
    siregex = sire_not.sub("\\1~", siregex)
    return siregex


def regex_to_proposition(regex: str) -> str:
    return sire_not.sub("\\1~", sire_and.sub(" ", regex))


if __name__ == "__main__":
    try:
        while True:
            line = input()
            print("Signal Regex: {}".format(line))
            regex = to_regex(line)
            print("Regex after transformation: {}".format(regex))
            siregex = from_regex(regex)
            print("After backward transformation: {}".format(siregex))
    except EOFError:
        pass
    except KeyboardInterrupt:
        print()
