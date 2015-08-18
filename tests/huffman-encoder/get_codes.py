#!/usr/bin/env python3

import shlex
import subprocess
import argparse
from subprocess import Popen
from time import sleep
import select


def execute_shell(cmd, input=''):
    """
    Execute cmd, send input to stdin.
    Return returncode, stdout, stderr.
    """

    proc_stdin = subprocess.PIPE if input != '' and input is not None else None
    proc_input = input if input != '' and input is not None else None

    args = shlex.split(cmd)

    p = subprocess.Popen(args,
                         stdin=proc_stdin,
                         stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE)

    out, err = p.communicate(proc_input)

    return p.returncode, \
           str(out, encoding='utf-8'), \
           str(err, encoding='utf-8')


def to_str_ret_out_err(ret, out, err):
    res = ''
    res += "return:%i" % ret + '\n'
    res += "out:\n"
    res += out + '\n'
    res += "err:\n"
    res += err
    return res


def extend(i_bin, width):
    """
    >>> print(extend('10', 2))
    10
    >>> print(extend('11', 5))
    00011
    """
    assert len(i_bin) <= width
    return '0'*(width-len(i_bin)) + i_bin


def main(huffman_model_name):
    p = Popen(['stdbuf', '-oL', 'aigsim', huffman_model_name],
              # stdbuf forces output to be line-buffered (bufsize=1 didn't work)
              stdin=subprocess.PIPE,
              stdout=subprocess.PIPE,
              stderr=subprocess.STDOUT)

    cipher_by_letter = dict()
    for i in range(1,28):   # all letters {A..Z, space} -> [1..27]
        cipher = ''  # left to right reading: leftmost is sent first
        print('getting cipher for', i, '-------------')
        while True:
            i_bin = bin(i)[2:]
            i_bin_width5 = extend(i_bin, 5)

            p.stdin.write(bytes(i_bin_width5+'\n', 'utf-8'))
            p.stdin.flush()

            response = str(p.stdout.readline(), 'utf-8')\
                .strip()
            assert response and len(response.split()) == 4, response

            output = response.split()[2]
            assert len(output) == 2, output
            cipher_bit, done = output
            cipher += cipher_bit

            print('current cipher:', cipher)

            if done == '1':
                cipher_by_letter[i] = cipher
                break

    print('\n'.join(map(str, cipher_by_letter.items())))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Name me!')

    parser.add_argument('huffman_model', metavar='huffman_model',
                        type=str,
                        help='huffman_model input file name '
                             '(the model should have outputs cipher,done)')

    # parser.add_argument('--flag', action='store_true',
    #                     required=False, default=False,
    #                     help='some flag')

    args = parser.parse_args()
    # print(args)
    exit(main(args.huffman_model))

