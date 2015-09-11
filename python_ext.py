def readfile(file_name):
    with open(file_name) as f:
        return f.read()


def stripped(str_lines) -> list:
    return [l.strip() for l in str_lines if l.strip()]

def stripped_e(str_lines) -> list:
    return [l.strip() for l in str_lines]

def find(lambda_func, l) -> int:
    for i, e in enumerate(l):
        if lambda_func(e):
            return i
    return -1


def find_all(lambda_func, l) -> list:   # returns list of indices
    return list(map(lambda i_l: i_l[0],
                    filter(lambda i_l: lambda_func(i_l[1]), enumerate(l))))
