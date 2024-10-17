def find_index(li, func):
    for i, v in enumerate(li):
        if func(v):
            return i
    return -1


def find(li, func):
    return next(iter(filter(func, li)), None)
