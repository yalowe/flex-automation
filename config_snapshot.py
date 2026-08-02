from pathlib import Path


class ConfigSnapshot:

    def __init__(self, irrigation):
        self.irrigation = irrigation

    def save(self):

        Path("logs").mkdir(exist_ok=True)

        programs = self.irrigation.programs_info()
        shifts = self.irrigation.shifts_info()
        recipes = self.irrigation.recipes_info()

        print("\n========== PROGRAMS ==========")
        print(programs)

        print("\n========== SHIFTS ==========")
        print(shifts)

        print("\n========== RECIPES ==========")
        print(recipes)

        self._save(
            "logs/programs.txt",
            str(programs),
        )

        self._save(
            "logs/shifts.txt",
            str(shifts),
        )

        self._save(
            "logs/recipes.txt",
            str(recipes),
        )

    @staticmethod
    def _save(path, content):
        with open(
            path, "w", encoding="utf-8",
        ) as f:
            f.write(content)
