"""
Recursively Merge Dictionaries
"""

# from copy import deepcopy
from functools import reduce


def merge(first, second, path=None, update=True):
    """Merge two dictionaries together, destructive to both dictionaries"""
    if path is None:
        path = []
    for key in second:
        if key in first:
            if isinstance(first[key], dict) and isinstance(second[key], dict):
                merge(first[key], second[key], path=path + [str(key)], update=update)
            elif first[key] == second[key]:
                pass  # same leaf value
# this code was designed to handle lists of dictionaries, but really we probably want
# to replace rather than merge or extend lists
#            elif isinstance(first[key], list) and isinstance(second[key], list):
#                for idx, val in enumerate(second[key]):
#                    if isinstance(first[key], dict) and isindex(second[key], dict):
#                        first[key][idx] = merge(first[key][idx], second[key][idx],
#                                                path=path + [str(key), str(idx)], update=update)
#                else:
#                    first[key].extend(second[key])
            elif update:
                first[key] = second[key]
            else:
                raise KeyError("Merge conflict at `{}'".format('.'.join(path + [str(key)])))
        else:
            first[key] = second[key]
    return first


def remerge(dicts):
    """Merge a series of dictionaries (destructive)"""
    return reduce(merge, dicts)
