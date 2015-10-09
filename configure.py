#!/usr/bin/env python3

import argparse
import os
from console_helpers import print_green


CONFIG_PY_NAME = 'config.py'
CONFIG_SH_NAME = 'config.sh'

CONFIG_PY_TEXT = """
AISY = '/home/ayrat/projects/aisy/aisy.py'
GOAL = '/home/ayrat/projects/GOAL-20141117/gc'
"""
CONFIG_SH_TEXT = """
IIMC_CHECKER=/home/ayrat/projects/iimc-2.0/iimc
"""


def _get_root_dir() -> str:
    return os.path.dirname(os.path.abspath(__file__))


def _user_confirmed(question:str):
    answer = input(question + ' [y/n] ').strip()
    assert answer in 'yYnN', answer
    return answer in 'yY'


def _check_files_exist(files):
    existing = list(filter(lambda f: os.path.exists(f), files))
    return existing


def main():
    config_py = os.path.join(_get_root_dir(), CONFIG_PY_NAME)
    existing = _check_files_exist([CONFIG_PY_NAME, CONFIG_SH_NAME])
    if not existing or \
            _user_confirmed('{files} already exist(s).\n'.format(files=existing) +
                            'Replace?'):
        with open(config_py, 'w') as file:
            file.write(CONFIG_PY_TEXT)
        with open(CONFIG_SH_NAME, 'w') as file:
            file.write(CONFIG_SH_TEXT)

        print_green('Created {files}.\n'
                    'Now edit them with your paths.'.
                    format(files=[CONFIG_PY_NAME, CONFIG_SH_NAME]))

        return True

    return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=
                                     'Generate local configuration file')

    args = parser.parse_args()
    res = main()
    print(['not done', 'done'][res])
    exit(res)
