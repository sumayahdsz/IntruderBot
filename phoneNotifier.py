from time import sleep
from notifier import Notifier, IntruderInfo
import pywhatkit as pwk

class PhoneNotifier(Notifier):
    """
    Notifies users through whatsapp messages.

    Assumes all provided numbers are valid and are all on whatsapp.
    """

    # data_list is used for phone numbers

    def __init__(self, phone_numbers_list_file_path, is_enabled_setting_file_path):
        setting_for_is_enabled = "PhoneNotifierOn"
        super().__init__(phone_numbers_list_file_path, setting_for_is_enabled, is_enabled_setting_file_path)

    def notify(self, intruder_info:IntruderInfo):
        if not self.get_enabled():
            return
        sleep(8) # wait a bit since it takes a little time for the generated image to be saved sometimes
        # Send intruder detected message on whatsapp
        for phone_number in self.get_data_list():
            print(intruder_info.image_path)
            print("send whatsapp message to " + phone_number)
            pwk.sendwhats_image(
                phone_number,
                intruder_info.image_path,
                "Intruder detected",
                tab_close=True
            )
