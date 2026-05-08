"""
course_loader.py
Parses course allocation files and returns a dict mapping semester number (1-8)
to a list of course titles for that semester.
"""

import os
import re

# Maps department to its respective filename
_DEPT_FILES = {
    "CSE": "CSE_Course_allocate.txt",
    "Physics": "Physics_Course_allocate.txt",
    "Chemistry": "Chemistry_Course_allocate.txt",
    "Math": "Math_Course_allocate.txt"
}

# Maps ordinal words to integers
_ORDINAL = {
    "first": 1, "second": 2, "third": 3, "fourth": 4
}

# Header pattern: captures the year-ordinal and semester-ordinal as named groups
_HEADER_PATTERN = re.compile(
    r"(?P<year>First|Second|Third|Fourth)\s+Year\s+(?P<sem>First|Second)\s+Semester",
    re.IGNORECASE,
)

# Course line pattern:
# CSE Style: "0613 04 CSE 1101 Structured Programming Languages 3.0"
# Physics/Chem Style: "PHY 0533 1121 Mechanics and Properties of Matter 3.0"
_COURSE_PATTERN = re.compile(
    r"^\s*(?:[A-Z]{3,4}\s+\d{4}\s+\d{4,5}|\d{4,5}\s+\d{2}\s+[A-Z]{3,4}\s+[\w\-]+)\s+(.+?)\s+\d+\.\d+\s*$",
    re.IGNORECASE
)


def _header_to_semester(match: re.Match) -> int:
    """
    Converts a _HEADER_PATTERN match to a global semester number (1-8).
    Formula: (year_number - 1) * 2 + semester_within_year
    """
    year_num = _ORDINAL[match.group("year").lower()]
    sem_num  = _ORDINAL[match.group("sem").lower()]
    return (year_num - 1) * 2 + sem_num


def load_courses(dept: str) -> dict:
    """
    Reads the appropriate allocation file and returns a dict:
        { semester_number: [course_title, ...], ... }
    """
    filename = _DEPT_FILES.get(dept, "Course_allocate.txt")
    file_path = os.path.join(os.path.dirname(__file__), "..", filename)
    
    courses: dict = {}
    current_sem = None

    try:
        with open(file_path, "r", encoding="utf-8-sig") as f:
            lines = f.readlines()
    except FileNotFoundError:
        # Fallback to default if dept-specific file not found
        if filename != "Course_allocate.txt":
            default_path = os.path.join(os.path.dirname(__file__), "..", "Course_allocate.txt")
            try:
                with open(default_path, "r", encoding="utf-8-sig") as f:
                    lines = f.readlines()
            except FileNotFoundError:
                return courses
        else:
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


# Module-level cache so files are read only once per process
_COURSES_CACHE: dict = {}


def get_courses(semester: int, dept: str = "CSE") -> list:
    """
    Returns the list of course titles for the given semester (1-8) and department.
    """
    global _COURSES_CACHE
    if dept not in _COURSES_CACHE:
        _COURSES_CACHE[dept] = load_courses(dept)
    
    return _COURSES_CACHE[dept].get(semester, [])