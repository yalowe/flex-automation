class DeviceService:

    def __init__(self, controller):
        self.controller = controller

    def get_device_info(self):
        return self.controller.send("Device Info")

    def get_programs(self):
        return self.controller.send("IrrProg Info")

    def get_shifts(self):
        return self.controller.send("Shift Info")

    def get_recipes(self):
        return self.controller.send("Recipe Info")

    def get_general_config(self):
        return self.controller.send("IrrGen Info")

    def get_alerts(self):
        return self.controller.send("IrrAlarm Info")

    def get_do_map(self):
        return self.controller.send("IrrDOMap Info")

    def get_di_map(self):
        return self.controller.send("IrrDIMap Info")

    def get_queue(self):
        return self.controller.send("IrrQueue Print")

    def get_ai_map(self):
        return self.controller.send("IrrAIMap Info")
