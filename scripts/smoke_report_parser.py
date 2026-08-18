from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from services.report_parser import ReportParser


def main() -> None:
    report = """Report type: Completed
Irrigation Data: Actual started time: 08:10:11
Delivered quantity: 12345
Delivered time: 678
Dosing Channel: 1, foo
Plan amount: 200
Method: Calculated Quantity
Units: Quant
Flow: 30070
Delivered quantity: 150
Delivered time: 50
Remain quantity: 25
Remain time: 7
Dosing Channel: 2, bar
Plan amount: 100
Method: Spread
Units: Quantity
Flow: 1000
Delivered quantity: 80
Delivered time: 35
Remain quantity: 10
Remain time: 3
Finish reason: Completed
"""

    channels = ReportParser.parse_dosing_channels(report)
    summary = ReportParser.parse_completed_report(report)
    finish = ReportParser.parse_finish_reason(report)
    start = ReportParser.parse_actual_start_time(report)

    assert 1 in channels, "Channel 1 should be parsed"
    assert channels[1]["method"] == "Calculated Quantity"
    assert channels[2]["units"].lower() == "quantity"

    assert summary["water_delivered"] == 12345
    assert summary["dosing_delivered"] == 230
    assert summary["dosing_remaining"] == 35
    assert summary["dosing_time"] == 50

    assert finish == "Completed"
    assert start == "08:10:11"

    print("smoke_report_parser: PASS")


if __name__ == "__main__":
    main()
