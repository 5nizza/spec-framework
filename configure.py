#!/usr/bin/env python3

import argparse
from inspect import cleandoc
import os
from console_helpers import print_green


CONFIG_PY_NAME = 'config.py'


def _get_root_dir() -> str:
    return os.path.dirname(os.path.abspath(__file__))


def _user_confirmed(question:str):
    answer = input(question + ' [y/n] ').strip()
    assert answer in 'yYnN', answer
    return answer in 'yY'


def main():
    text = """
    AISY = '/home/ayrat/projects/aisy/aisy.py'
    GOAL = '/home/ayrat/projects/GOAL-20141117/gc'
    """
    text = cleandoc(text)
    config_py = os.path.join(_get_root_dir(), CONFIG_PY_NAME)
    if os.path.exists(config_py) and _user_confirmed('{config_py} already exists.\n'.format(config_py=CONFIG_PY_NAME) +
                                                     'Replace?')\
            or not os.path.exists(config_py):
        with open(config_py, 'w') as file:
            file.write(text)
            print_green('')
            print_green('Created {config_py}.\n'
                        'Now edit it with your paths.'.
                        format(config_py=CONFIG_PY_NAME))
            return True

    return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=
                                     'Generate local configuration file')

    args = parser.parse_args()
    res = main()
    print(['not done', 'done'][res])
    exit(res)
