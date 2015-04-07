def readfile(file_name):
    with open(file_name) as f:
        return f.read()


def stripped(str_lines) -> list:
    return [l.strip() for l in str_lines if l.strip()]


def find(lambda_func, l) -> int:
    for i,e in enumerate(l):
        if lambda_func(e):
            return i
    return -1
