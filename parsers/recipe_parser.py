class RecipeParser:

    @staticmethod
    def parse_recipe(text: str, recipe_id: int):

        for line in text.splitlines():

            line = line.strip()

            if not line.startswith(str(recipe_id)):
                continue

            blocks = line.split("||")[1:5]

            channels = {}

            for channel_id, block in enumerate(
                    blocks,
                    start=1
            ):

                parts = [
                    p.strip()
                    for p in block.split("|")
                ]

                if len(parts) < 4:
                    continue

                method = parts[0]
                units = parts[1]
                enabled = parts[2] == "Yes"

                amount = None

                try:
                    amount = int(parts[3])
                except ValueError:
                    pass

                channels[channel_id] = {
                    "enabled": enabled,
                    "method": method or None,
                    "units": units or None,
                    "amount": amount,
                }

            return {
                "recipe_id": recipe_id,
                "channels": channels,
            }

        return None