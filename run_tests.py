#!/usr/bin/env python3
import os
import argparse
import re
from tempfile import NamedTemporaryFile
from nose.tools import assert_equal
from python_ext import readfile, stripped


MY_DIR = os.path.dirname(os.path.realpath(__file__))
############################################################################
# When used with --aisy flag, requires `aisy` synthesizer
# Change the paths according to your setup.
# Usage of aisy: aisy <input_file> -q
# Returns: 10 -- realizable, 20 -- unrealizable
from config import AISY

EXIT_STATUS_REALIZABLE = 10
EXIT_STATUS_UNREALIZABLE = 20

TESTS_DIRS = ["./tests/"]

# usage: spec_2_aag.py <smv_file>,
# returns 0 on success and prints the result to stdout
TOOL = os.path.join(MY_DIR, "spec_2_aag.py")
############################################################################


def execute_shell(cmd, input=''):
    import shlex
    import subprocess

    """
    Execute cmd, send input to stdin.
    :return: returncode, stdout, stderr.
    """

    proc_stdin = subprocess.PIPE if input != '' and input is not None else None
    proc_input = input if input != '' and input is not None else None

    args = shlex.split(cmd)

    p = subprocess.Popen(args,
                         stdin=proc_stdin,
                         stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE)

    out, err = p.communicate(proc_input)

    return p.returncode, str(out, encoding='utf-8'), str(err, encoding='utf-8')


def get_tmp_file_name():
    tmp = NamedTemporaryFile(delete=False)
    return tmp.name


def is_realizable(test):
    spec_status = stripped(readfile(test).splitlines())[-1]
    if re.fullmatch('-- *realizable', spec_status):
        return True
    if re.fullmatch('-- *unrealizable', spec_status):
        return False

    assert 0, 'spec status is unknown'


def status_to_str(exit_status):
    return ['unrealizable', 'realizable'][exit_status == EXIT_STATUS_REALIZABLE]


def convert_and_check(test):
    rc, out, err = execute_shell(TOOL + ' ' + test)

    if rc != 0:
        print()
        print(test)
        print('The tool returned a non-zero status: ', to_str_ret_out_err(rc, out, err))
        exit(1)

    return out


def to_str_ret_out_err(rc, out, err):
    res = 'ret=' + str(rc) + '\nout=' + str(out) + '\nerr=' + str(err)
    return res


def synthesize_spec(aag_spec:str, test_name:str) -> bool:
    tmp_file_name = get_tmp_file_name() + '.aag'
    with open(tmp_file_name, 'w') as f:
        f.write(aag_spec)

    cmd_line = AISY + ' ' + tmp_file_name + ' -q -r'
    print('  synthesizing: \n', cmd_line)
    ret, out, err = execute_shell(cmd_line)

    assert not err.strip(), err
    assert not out.strip(), out

    assert ret in [EXIT_STATUS_REALIZABLE, EXIT_STATUS_UNREALIZABLE], str(ret)

    os.remove(tmp_file_name)   # on fail, keep it

    return ret == EXIT_STATUS_REALIZABLE


def get_all_smv_files(directory:str):
    matching_files = list()
    for top, subdirs, files in os.walk(directory, followlinks=True):
        if 'notest' in files:  # ignore folders that contains file called notest
            continue
        for f in files:
            if f.endswith('.smv'):
                matching_files.append(os.path.join(MY_DIR, top, f))
    return matching_files


def main(synthesize):
    tests = []
    for td in TESTS_DIRS:
        tests.extend(get_all_smv_files(os.path.join(MY_DIR, td)))

    assert tests, 'no tests found'

    for t in tests:
        print('converting:\n' + TOOL + ' ' + t)
        aag_spec = convert_and_check(t)
        if synthesize:
            is_realizable_expected = is_realizable(t)
            is_realizable_actual = synthesize_spec(aag_spec, t)
            assert_equal(is_realizable_expected, is_realizable_actual, 'test failed: ' + t)
        print()

    print('ALL TESTS PASSED')
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Tests runner')

    parser.add_argument('--aisy', action='store_true',
                        required=False, default=False,
                        help='synthesize the resulting spec, default: False. '
                             'NOTE: modify the path to aisy.')

    args = parser.parse_args()

    exit(main(args.aisy))
