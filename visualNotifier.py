from notifier import Notifier, IntruderInfo
from myColours import MY_COLOURS

class VisualNotifier(Notifier):
    def __init__(self, is_enabled_setting_file_path, app):
        self.setting_for_is_enabled = "VisualNotifierOn"
        self.app = app
        
        # this notifier does not store data, so we will not touch data and just pass in settings file path
        super().__init__(is_enabled_setting_file_path, self.setting_for_is_enabled, is_enabled_setting_file_path)
    
    def notify(self, intruder_info:IntruderInfo):
        if not self.get_enabled():
            return
        human_readable_detection_time = intruder_info.detection_time.strftime('%d %B (%A) at %I:%M:%S %p %Z')        
        self.app.reset_intruder_detection_command(text="Intruder Detected\nat {day}!".format(day=human_readable_detection_time), primary_color=MY_COLOURS["dark_red"])
        self.app.set_intruder_image(intruder_info.image_path)

