import re


class ShiftParser:

    @staticmethod
    def parse_program(text: str, program_id: int):

        for line in text.splitlines():

            line = line.strip()

            if not line.startswith(str(program_id)):
                continue

            recipe_amount_match = re.search(
                r"\|\|\s*(\d+)\s*\|\s*(\d+)\s*\|",
                line,
            )

            recipe_id = int(recipe_amount_match.group(1))
            amount = int(recipe_amount_match.group(2))

            valves = [int(v) for v in re.findall(r"\|\s+(\d+)\|\|", line)]

            return {
                "shift_id": 1,
                "recipe_id": recipe_id,
                "amount": amount,
                "valves": valves,
            }

        return None
