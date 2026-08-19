from __future__ import annotations

import pytest


def pytest_addoption(parser):
    group = parser.getgroup("flex hardware")
    group.addoption(
        "--flex-port",
        action="store",
        default="COM5",
        help="FLEX controller serial port",
    )
    group.addoption(
        "--flex-baud",
        action="store",
        type=int,
        default=115200,
        help="FLEX controller baud rate",
    )
    group.addoption(
        "--flex-runs",
        action="store",
        type=int,
        default=1,
        help="Number of scenario loops",
    )


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "hardware: test requires a connected FLEX controller and COM port",
    )


@pytest.fixture
def flex_cli_options(request):
    return {
        "port": request.config.getoption("--flex-port"),
        "baud": request.config.getoption("--flex-baud"),
        "runs": request.config.getoption("--flex-runs"),
        "allure_dir": request.config.getoption("--alluredir"),
    }
