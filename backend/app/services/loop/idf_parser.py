import re
from pathlib import Path

from pydantic import BaseModel


class IDFData(BaseModel):
    heating_occupied_c: float = 21.0
    heating_unoccupied_c: float = 15.6
    cooling_occupied_c: float = 24.0
    cooling_unoccupied_c: float = 26.7


def parse_idf(idf_path: Path) -> IDFData:
    content = idf_path.read_text(encoding="latin-1")
    data = IDFData()

    htg_match = re.search(
        r"Schedule:Compact,\s*HTGSETP_SCH,(.*?);",
        content,
        re.DOTALL,
    )
    if htg_match:
        block = htg_match.group(1)
        untils = re.findall(r"Until:\s*[\d:]+,([\d.]+)", block)
        if len(untils) >= 2:
            data.heating_unoccupied_c = float(untils[0])
            data.heating_occupied_c = float(untils[1])

    clg_match = re.search(
        r"Schedule:Compact,\s*CLGSETP_SCH,(.*?);",
        content,
        re.DOTALL,
    )
    if clg_match:
        block = clg_match.group(1)
        untils = re.findall(r"Until:\s*[\d:]+,([\d.]+)", block)
        if len(untils) >= 2:
            data.cooling_unoccupied_c = float(untils[0])
            data.cooling_occupied_c = float(untils[1])

    return data


def modify_idf(
    idf_path: Path,
    output_path: Path,
    heating_occupied_c: float | None = None,
    cooling_occupied_c: float | None = None,
) -> Path:
    content = idf_path.read_text(encoding="latin-1")

    if heating_occupied_c is not None:
        content = re.sub(
            r"(Schedule:Compact,\s*HTGSETP_SCH,.*?Until:\s*06:00,)([\d.]+)(,.*?Until:\s*22:00,)([\d.]+)",
            lambda m: f"{m.group(1)}{m.group(2)}{m.group(3)}{heating_occupied_c}",
            content,
            flags=re.DOTALL,
        )

    if cooling_occupied_c is not None:
        content = re.sub(
            r"(Schedule:Compact,\s*CLGSETP_SCH,.*?Until:\s*06:00,)([\d.]+)(,.*?Until:\s*22:00,)([\d.]+)",
            lambda m: f"{m.group(1)}{m.group(2)}{m.group(3)}{cooling_occupied_c}",
            content,
            flags=re.DOTALL,
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(content, encoding="latin-1")
    return output_path
