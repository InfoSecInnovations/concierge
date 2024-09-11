def find_index(li, func):
    for i, v in enumerate(li):
        if func(v):
            return i
    return -1
