import re


class ShiftParser:

    @staticmethod
    def parse_program(text: str, program_id: int):

        for line in text.splitlines():

            line = line.strip()

            if not line.startswith(str(program_id)):
                continue

            recipe_match = re.search(r"\|\|\s*(\d+)\s*\|", line)

            recipe_id = int(recipe_match.group(1))

            valves = [int(v) for v in re.findall(r"\|\s+(\d+)\|\|", line)]

            return {"recipe_id": recipe_id, "valves": valves}

        return None
