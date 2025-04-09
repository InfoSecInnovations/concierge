from typing import TypeVar, Callable, Any

def find_index(li, func):
    for i, v in enumerate(li):
        if func(v):
            return i
    return -1

T = TypeVar("T")

def find(li: list[T], func: Callable[[T], Any]) -> T | None:
    return next(iter(filter(func, li)), None)
