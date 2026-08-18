import time


def print_summary(stats) -> None:
    print("\n")
    print("=" * 100)
    print("CURRENT SUMMARY")
    print("=" * 100)

    for scenario_name, result in stats.items():
        print(
            f"{scenario_name:<35} : "
            f"{result['pass']} PASS | "
            f"{result['fail']} FAIL"
        )

    print("=" * 100)


def run_nightly(e2e_tests, scenarios, run_count: int = 1) -> None:
    run_number = max(0, run_count)

    stats = {
        scenario.name: {
            "pass": 0,
            "fail": 0,
        }
        for scenario in scenarios
    }

    while run_number > 0:
        print("=" * 100)

        for scenario in scenarios:
            print("-" * 100)
            print(f"RUNNING: {scenario.name} " f"(Program ID {scenario.program_id})")
            print("-" * 100)

            try:
                e2e_tests.run_scenario(scenario)

                stats[scenario.name]["pass"] += 1

                print(f"PASSED: {scenario.name} " f"(Program ID {scenario.program_id})")

            except Exception as ex:
                stats[scenario.name]["fail"] += 1

                print(f"FAILED: {scenario.name} " f"(Program ID {scenario.program_id})")

                print(ex)

            time.sleep(10)

        print_summary(stats)

        run_number -= 1
