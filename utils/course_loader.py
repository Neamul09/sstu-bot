"""
course_loader.py
Parses Course_allocate.txt and returns a dict mapping semester number (1-8)
to a list of course titles for that semester.
"""

import os
import re

# Path to the course allocation file (project root, relative to this utils/ dir)
_COURSE_FILE = os.path.join(os.path.dirname(__file__), "..", "Course_allocate.txt")

# Maps ordinal words to integers
_ORDINAL = {
    "first": 1, "second": 2, "third": 3, "fourth": 4
}

# Header pattern: captures the year-ordinal and semester-ordinal as named groups
# e.g. "Second Year First Semester"  =>  year="Second", sem="First"
_HEADER_PATTERN = re.compile(
    r"(?P<year>First|Second|Third|Fourth)\s+Year\s+(?P<sem>First|Second)\s+Semester",
    re.IGNORECASE,
)

# Course line pattern:
# e.g.  "0613 04 CSE 1101 Structured Programming Languages 3.0"
#        ^--------code-------^  ^---------title-----------^ ^credit^
_COURSE_PATTERN = re.compile(
    r"^\s*\d{4}\s+\d{2}\s+\w+\s+[\w\-]+\s+(.+?)\s+\d+\.\d+\s*$"
)


def _header_to_semester(match: re.Match) -> int:
    """
    Converts a _HEADER_PATTERN match to a global semester number (1-8).
    Formula: (year_number - 1) * 2 + semester_within_year
    """
    year_num = _ORDINAL[match.group("year").lower()]
    sem_num  = _ORDINAL[match.group("sem").lower()]
    return (year_num - 1) * 2 + sem_num


def load_courses() -> dict:
    """
    Reads Course_allocate.txt and returns a dict:
        { semester_number: [course_title, ...], ... }
    for semesters 1-8.
    """
    courses: dict = {}
    current_sem = None

    try:
        with open(_COURSE_FILE, "r", encoding="utf-8-sig") as f:
            lines = f.readlines()
    except FileNotFoundError:
        return courses

    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            continue

        # Detect a semester header line
        hm = _HEADER_PATTERN.search(line)
        if hm:
            current_sem = _header_to_semester(hm)
            if current_sem not in courses:
                courses[current_sem] = []
            continue

        # No active semester yet
        if current_sem is None:
            continue

        # Skip table-header / total lines
        ll = line.lower()
        if ll.startswith("total") or ll.startswith("course code"):
            continue

        # Parse course title from a course-code line
        m = _COURSE_PATTERN.match(line)
        if m:
            title = m.group(1).strip()
            if title and title not in courses[current_sem]:
                courses[current_sem].append(title)

    return courses


# Module-level cache so the file is read only once per process
_COURSES_CACHE: dict | None = None


def get_courses(semester: int) -> list:
    """
    Returns the list of course titles for the given semester (1-8).
    Cached after first call.
    """
    global _COURSES_CACHE
    if _COURSES_CACHE is None:
        _COURSES_CACHE = load_courses()
    return _COURSES_CACHE.get(semester, [])