from __future__ import annotations

import time
import serial

from flex.models import CommandResult


class FlexController:

    def __init__(self, port: str, baudrate: int = 115200, timeout: int = 2):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.serial = None
        self.monitoring_service = None

    def set_monitoring_service(self, monitoring_service) -> None:
        self.monitoring_service = monitoring_service

    def connect(self) -> None:
        self.serial = serial.Serial(
            port=self.port,
            baudrate=self.baudrate,
            timeout=self.timeout,
        )

    def disconnect(self) -> None:
        if self.serial:
            self.serial.close()

    def send(self, command: str) -> CommandResult:
        if not self.serial:
            raise RuntimeError("Not connected")

        self.serial.reset_input_buffer()

        self.serial.write(f"{command}\n".encode("utf-8"))

        time.sleep(1)

        response = ""

        while self.serial.in_waiting:
            response += self.serial.readline().decode(errors="ignore")

        

        # print("response: \n", response)

        success = "Status:OK" in response and "Status:Error" not in response

        if self.monitoring_service is not None:
            try:
                self.monitoring_service.capture(command, response, success)
            except Exception as ex:
                print(f"Monitoring capture failed: {ex}")

        return CommandResult(command=command, success=success, response=response)
