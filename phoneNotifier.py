from time import sleep
import tkinter
from notifier import Notifier, IntruderInfo
import pywhatkit as pwk
# import time

class PhoneNotifier(Notifier):
    """
    Notifies users through whatsapp messages.

    Assumes all provided numbers are valid and are all on whatsapp.
    """

    # data_list is used for phone numbers

    def __init__(self, phone_numbers_list_file_path, is_enabled_setting_file_path):
        """
        Initialise a whatsapp notifier
        """
        setting_for_is_enabled = "PhoneNotifierOn"
        super().__init__(phone_numbers_list_file_path, setting_for_is_enabled, is_enabled_setting_file_path)

    def notify(self, intruder_info:IntruderInfo):
        """
        Send whatsapp messages if the setting is enabled.
        """
        if not self.get_enabled():
            return
        sleep(8) # wait a bit since it takes a little time for the generated image to be saved sometimes
        # Send intruder detected message on whatsapp
        for phone_number in self.get_data_list():
            print("send whatsapp message to " + phone_number)
            try:
                pwk.sendwhats_image(
                    phone_number,
                    intruder_info.image_path,
                    "Intruder detected",
                    tab_close=True
                )
            except pwk.core.exceptions.CountryCodeException:
                # incorrect country code exceptions are sometimes not caught by the regex. So we show a popup for this issue and skip the number.
                tkinter.messagebox.showerror(title="invalid phone number", message=f"Invalid phone number {phone_number} entered. Skipping alerting number.")
        # timing util
        # phone_time = time.perf_counter()
        # print(f"phone finished at: {phone_time} seconds")
