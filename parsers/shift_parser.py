import re


class ShiftParser:

    @staticmethod
    def _decode_valve_mask(mask_text: str) -> list[int]:
        """Shift Info encodes valves as a hex bitmask (e.g. "10" => 0x10 => valve 5)."""
        mask_text = (mask_text or "").strip()
        if not mask_text:
            return []

        try:
            mask_value = int(mask_text, 16)
        except ValueError:
            return []

        valves = []
        bit_index = 0
        while mask_value:
            if mask_value & 1:
                valves.append(bit_index + 1)
            mask_value >>= 1
            bit_index += 1

        return valves

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

            valve_matches = re.findall(r"\|\s+([0-9A-Fa-f]+)\|\|", line)
            valves = []
            for valve_mask_text in valve_matches:
                valves.extend(ShiftParser._decode_valve_mask(valve_mask_text))

            # Backward-compatible fallback for unexpected non-mask data.
            if not valves:
                valves = [int(v) for v in re.findall(r"\|\s+(\d+)\|\|", line)]

            return {
                "shift_id": 1,
                "recipe_id": recipe_id,
                "amount": amount,
                "valves": valves,
            }

        return None
