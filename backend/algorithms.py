"""
algorithms.py — Hand-rolled sorting and searching engine for TaskFlow.

Section 2 of the TaskFlow assignment.

Functions
---------
insertion_sort(records, key)
    Sort a list of dicts in-place by record[key].

binary_search(sorted_records, target_value, key)
    Search a sorted list using the standard low/high/mid pointer approach.
    Returns the index of a matching record, or -1 if not found.

linear_search(records, target_value, key)
    Scan every record in order and return the index of the first match,
    or -1 if absent.

Counting wrappers (for benchmark / comparison counting)
-------------------------------------------------------
insertion_sort_count(records, key)       → int  (comparison count)
binary_search_count(sorted_records, target_value, key)
                                          → {"index": int, "comparison_count": int}
linear_search_count(records, target_value, key)
                                          → {"index": int, "comparison_count": int}

Complexity reference
--------------------
insertion_sort  : best O(n), worst O(n²)
binary_search   : best O(1), worst O(log n)
linear_search   : best O(1), worst O(n)
"""

from typing import Any, Dict, List, Optional, Union


# ═══════════════════════════════════════════════════════════════════
# Core algorithms
# ═══════════════════════════════════════════════════════════════════

def insertion_sort(records: List[Dict], key: str) -> None:
    """
    Sort *records* in place by record[key] using insertion sort.

    The function mutates the list directly and returns nothing.

    Time complexity
    ---------------
    Best case  : O(n)   — list already sorted
    Worst case : O(n²)  — list sorted in reverse order
    """
    for i in range(1, len(records)):
        current = records[i]
        current_val = current[key]
        j = i - 1
        while j >= 0 and records[j][key] > current_val:
            records[j + 1] = records[j]
            j -= 1
        records[j + 1] = current


def binary_search(
    sorted_records: List[Dict],
    target_value: Any,
    key: str,
) -> int:
    """
    Search *sorted_records* (sorted ascending by *key*) for a record
    whose record[key] == target_value.

    Returns the index of the matching record, or -1 if no match is found.

    Time complexity
    ---------------
    Best case  : O(1)      — target is the middle element
    Worst case : O(log n)  — target not present (or at an extreme)
    """
    low = 0
    high = len(sorted_records) - 1

    while low <= high:
        mid = (low + high) // 2
        mid_val = sorted_records[mid][key]

        if mid_val == target_value:
            return mid
        elif mid_val < target_value:
            low = mid + 1
        else:
            high = mid - 1

    return -1


def linear_search(
    records: List[Dict],
    target_value: Any,
    key: str,
) -> int:
    """
    Scan every record and return the index of the first record whose
    record[key] == target_value, or -1 if absent.

    Time complexity
    ---------------
    Best case  : O(1)  — target is the first element
    Worst case : O(n)  — target not present
    """
    for i, record in enumerate(records):
        if record[key] == target_value:
            return i
    return -1


# ═══════════════════════════════════════════════════════════════════
# Counting wrappers  (same logic — different return contracts)
# ═══════════════════════════════════════════════════════════════════

def insertion_sort_count(records: List[Dict], key: str) -> int:
    """
    Sort *records* in place (same as insertion_sort) and return
    the total number of comparisons made.

    Returns
    -------
    int — total comparisons performed
    """
    comparisons = 0
    for i in range(1, len(records)):
        current = records[i]
        current_val = current[key]
        j = i - 1
        while j >= 0:
            comparisons += 1          # the comparison records[j][key] > current_val
            if records[j][key] > current_val:
                records[j + 1] = records[j]
                j -= 1
            else:
                break
        records[j + 1] = current
    return comparisons


def binary_search_count(
    sorted_records: List[Dict],
    target_value: Any,
    key: str,
) -> Dict[str, Union[int, None]]:
    """
    Binary search with comparison counting.

    Returns
    -------
    {"index": int, "comparison_count": int}
    index is the found position, or -1 if not found.
    """
    low = 0
    high = len(sorted_records) - 1
    comparisons = 0
    result_index = -1

    while low <= high:
        mid = (low + high) // 2
        mid_val = sorted_records[mid][key]
        comparisons += 1              # each iteration performs one comparison

        if mid_val == target_value:
            result_index = mid
            break
        elif mid_val < target_value:
            low = mid + 1
        else:
            high = mid - 1

    return {"index": result_index, "comparison_count": comparisons}


def linear_search_count(
    records: List[Dict],
    target_value: Any,
    key: str,
) -> Dict[str, Union[int, None]]:
    """
    Linear search with comparison counting.

    Returns
    -------
    {"index": int, "comparison_count": int}
    index is the found position, or -1 if not found.
    """
    comparisons = 0
    for i, record in enumerate(records):
        comparisons += 1              # each element visited is one comparison
        if record[key] == target_value:
            return {"index": i, "comparison_count": comparisons}

    return {"index": -1, "comparison_count": comparisons}
