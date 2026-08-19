from typing import List, Dict, Any, Optional

EDUCATION_SYSTEMS: Dict[str, Dict[str, Any]] = {
    "UK": {
        "name": "United Kingdom (England / Wales)",
        "levels": {
            0: "Reception",
            1: "Year 1",
            2: "Year 2",
            3: "Year 3",
            4: "Year 4",
            5: "Year 5",
            6: "Year 6",
            7: "Year 7",
            8: "Year 8",
            9: "Year 9",
            10: "Year 10",
            11: "Year 11",
            12: "Year 12",
            13: "Year 13",
        },
    },
    "USA": {
        "name": "United States",
        "levels": {
            0: "Kindergarten",
            1: "Grade 1",
            2: "Grade 2",
            3: "Grade 3",
            4: "Grade 4",
            5: "Grade 5",
            6: "Grade 6",
            7: "Grade 7",
            8: "Grade 8",
            9: "Grade 9",
            10: "Grade 10",
            11: "Grade 11",
            12: "Grade 12",
            13: "Grade 12+ (Post-Secondary)",
        },
    },
    "CANADA": {
        "name": "Canada",
        "levels": {
            0: "Kindergarten",
            1: "Grade 1",
            2: "Grade 2",
            3: "Grade 3",
            4: "Grade 4",
            5: "Grade 5",
            6: "Grade 6",
            7: "Grade 7",
            8: "Grade 8",
            9: "Grade 9",
            10: "Grade 10",
            11: "Grade 11",
            12: "Grade 12",
            13: "Grade 12+",
        },
    },
    "AUSTRALIA": {
        "name": "Australia",
        "levels": {
            0: "Foundation / Prep",
            1: "Year 1",
            2: "Year 2",
            3: "Year 3",
            4: "Year 4",
            5: "Year 5",
            6: "Year 6",
            7: "Year 7",
            8: "Year 8",
            9: "Year 9",
            10: "Year 10",
            11: "Year 11",
            12: "Year 12",
            13: "Year 12+",
        },
    },
}

def get_level_label(level: int, education_system: Optional[str] = "UK") -> str:
    system_key = (education_system or "UK").upper()
    if system_key not in EDUCATION_SYSTEMS:
        system_key = "UK"
    levels_map = EDUCATION_SYSTEMS[system_key]["levels"]
    return levels_map.get(level, f"Level {level}")

def get_available_levels(education_system: Optional[str] = "UK") -> List[Dict[str, Any]]:
    system_key = (education_system or "UK").upper()
    if system_key not in EDUCATION_SYSTEMS:
        system_key = "UK"
    levels_map = EDUCATION_SYSTEMS[system_key]["levels"]
    return [{"level": lvl, "label": label} for lvl, label in levels_map.items()]

def get_education_systems() -> List[Dict[str, str]]:
    return [{"id": code, "name": sys_data["name"]} for code, sys_data in EDUCATION_SYSTEMS.items()]
