"""
check_algorithms.py -- Section 2 automated PASS/FAIL checks for TaskFlow.

Verifies all algorithm functions against hand-checkable cases using plain
if/else statements (no assert, pytest, or unittest).

Run with:
    python check_algorithms.py

Prints one PASS/FAIL line for every case and exits with:
    code 0 -- all cases passed
    code 1 -- one or more cases failed
"""

import sys
import os

# Allow running from the repo root (taskflow/) as well as from backend/
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))

from algorithms import (
    insertion_sort,
    binary_search,
    linear_search,
    insertion_sort_count,
    binary_search_count,
    linear_search_count,
)

# -----------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------

failures = 0


def check(case_name, result, expected):
    """Evaluate one case and print PASS / FAIL."""
    global failures
    if result == expected:
        print(f"PASS: {case_name}")
    else:
        print(f"FAIL: {case_name} -- expected {expected!r}, got {result!r}")
        failures += 1


def check_true(case_name, condition):
    """Evaluate a boolean condition and print PASS / FAIL."""
    global failures
    if condition:
        print(f"PASS: {case_name}")
    else:
        print(f"FAIL: {case_name} -- condition was False")
        failures += 1


def section(title):
    print(f"\n-- {title} " + "-" * (60 - len(title)))


# =================================================================
# 1. insertion_sort -- edge cases
# =================================================================

section("insertion_sort edge cases")

# Case 1.1: empty list
empty = []
insertion_sort(empty, "val")
check("insertion_sort on empty list leaves it empty", empty, [])

# Case 1.2: single-element list
single = [{"val": 42}]
insertion_sort(single, "val")
check("insertion_sort on single-element list leaves element unchanged", single, [{"val": 42}])

# =================================================================
# 2. binary_search -- first, last, middle, absent
# =================================================================

section("binary_search first / last / middle / absent")

sorted_list = [
    {"key": 1},
    {"key": 3},
    {"key": 5},
    {"key": 7},
    {"key": 9},
]

# Case 2.1: value at first index (index 0)
check("binary_search finds value at first index", binary_search(sorted_list, 1, "key"), 0)

# Case 2.2: value at last index (index 4)
check("binary_search finds value at last index", binary_search(sorted_list, 9, "key"), 4)

# Case 2.3: value at middle index (index 2)
check("binary_search finds value at middle index", binary_search(sorted_list, 5, "key"), 2)

# Case 2.4: value absent -> returns -1
check("binary_search returns -1 when target is absent", binary_search(sorted_list, 99, "key"), -1)

# =================================================================
# 3. insertion_sort_count -- correct sort + int return > 0
# =================================================================

section("insertion_sort_count sorted result and comparison count type")

unsorted = [{"v": 5}, {"v": 2}, {"v": 8}, {"v": 1}, {"v": 4}]
cmp_count = insertion_sort_count(unsorted, "v")

# Case 3.1: list is correctly sorted after the call
expected_sorted = [{"v": 1}, {"v": 2}, {"v": 4}, {"v": 5}, {"v": 8}]
check("insertion_sort_count leaves list correctly sorted", unsorted, expected_sorted)

# Case 3.2: returns a plain int
check_true("insertion_sort_count returns a plain int", type(cmp_count) == int)

# Case 3.3: comparison count > 0 for multi-element list
check_true(
    "insertion_sort_count returns comparison_count > 0 for multi-element list",
    cmp_count > 0,
)

# =================================================================
# 4. binary_search_count -- index + comparison_count for present value
# =================================================================

section("binary_search_count correct index and comparison count")

sorted_dicts = [
    {"id": 10, "title": "alpha"},
    {"id": 20, "title": "beta"},
    {"id": 30, "title": "gamma"},
    {"id": 40, "title": "delta"},
    {"id": 50, "title": "epsilon"},
]
# Sort by title: alpha(0), beta(1), delta(2), epsilon(3), gamma(4)
insertion_sort(sorted_dicts, "title")

result_bsc = binary_search_count(sorted_dicts, "delta", "title")

# Case 4.1: "delta" is at index 2 in the sorted list
check(
    "binary_search_count returns correct index for 'delta'",
    result_bsc["index"],
    2,
)

# Case 4.2: comparison_count is an int > 0
check_true(
    "binary_search_count comparison_count is int > 0",
    isinstance(result_bsc["comparison_count"], int) and result_bsc["comparison_count"] > 0,
)

# =================================================================
# 5. linear_search_count -- absent value -> index -1, count == len
# =================================================================

section("linear_search_count absent value returns -1 and full-length count")

search_list = [
    {"name": "apple"},
    {"name": "banana"},
    {"name": "cherry"},
    {"name": "date"},
]

result_lsc = linear_search_count(search_list, "mango", "name")

# Case 5.1: index == -1 (not found)
check(
    "linear_search_count returns index = -1 for absent value",
    result_lsc["index"],
    -1,
)

# Case 5.2: comparison_count == len(list)
check(
    "linear_search_count comparison_count equals list length for absent value",
    result_lsc["comparison_count"],
    len(search_list),
)

# =================================================================
# 6. Additional correctness checks
# =================================================================

section("Additional: insertion_sort on already-sorted list")

already_sorted = [{"x": 1}, {"x": 2}, {"x": 3}]
cmp_already = insertion_sort_count(already_sorted, "x")
check(
    "insertion_sort_count on sorted list leaves it unchanged",
    already_sorted,
    [{"x": 1}, {"x": 2}, {"x": 3}],
)
check_true(
    "insertion_sort_count on already-sorted list returns int",
    type(cmp_already) == int,
)

section("Additional: linear_search finds first match")

multi = [{"v": 5}, {"v": 3}, {"v": 7}, {"v": 3}]
idx = linear_search(multi, 3, "v")
check("linear_search returns index of first match", idx, 1)

section("Additional: linear_search returns -1 when absent")

idx_absent = linear_search(multi, 99, "v")
check("linear_search returns -1 when target absent", idx_absent, -1)

# =================================================================
# Summary
# =================================================================

print()
print("=" * 60)
if failures == 0:
    print(f"All checks passed (0 failures).")
else:
    print(f"{failures} check(s) FAILED.")
print("=" * 60)

sys.exit(0 if failures == 0 else 1)
