#! /usr/bin/env python3
from re import sub

def to_regex(siregex: str) -> str:
    """
    Transforms a signal regex into an ordinary regex understood by GOAL.
    """
    regex = sub("[!~]", "not_", siregex)
    regex = sub(",", "_and_", regex)
    return regex

def from_regex(regex: str) -> str:
    """
    Transforms a modified GOAL regex back into signal regex.
    """
    siregex = sub("not_", "~", regex)
    siregex = sub("_and_", ",", siregex)
    return siregex

def regex_to_proposition(regex: str) -> str:
    return sub("not_", "~", sub("_and_", " ", regex))

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
