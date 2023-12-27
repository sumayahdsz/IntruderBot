from dataclasses import dataclass
import datetime as dt
from fileStorageUnit import FileStorageUnit

@dataclass
class IntruderInfo:
    """
    Intruder information used by notifiers
    """
    detection_time: dt.datetime
    image_path: str
    certainty_of_intruder: float
    
class Notifier(FileStorageUnit):
    """
    This class is the base interface for other notifiers.
    Notifiers alert users in different ways, whenever the notify method is called,
    as long as the notifier is enabled (__is_enabled is true).

    Since Notifier inherits from File Storage unit, it stores it's settings (whether it is enabled or not),
    when __store_is_enabled from file is called. This enables the program to save settings even after the user
    closes it, so that the same settings are applied when the user opens the program again.
    """
    def __init__(self, data_list_file_path, setting_for_is_enabled, is_enabled_setting_file_path):
        self.__is_enabled_setting_file_path = is_enabled_setting_file_path # where the is_enabled setting is stored
        self.__setting_for_is_enabled = setting_for_is_enabled # the variable in the file whose presence indicates this setting is on
        self.__load_is_enabled_from_file()
        super().__init__(data_list_file_path)

    def notify(self, intruder_info:IntruderInfo):
        """
        This is what the notifier does.
        This will be implemented by child classes that inherit from this class.
        """
        pass

    def get_enabled(self)->bool:
        """
        Return a boolean representing if the notifier is enabled (true if enabled)
        """
        return self.__is_enabled
    
    def set_enabled(self, is_enabled)->None:
        """
        Set the value for __is_enabled and store it in a file
        """
        self.__is_enabled = is_enabled
        self.__store_is_enabled_in_file()

    def __load_is_enabled_from_file(self):
        """
        Load the is_enabled setting from the file.

        Since all the notifiers will be using the same file to store their enabled settings,
        we know if a notifier is enabled if the __setting_for_is_enabled string value is in the file.
        """
        with open(self.__is_enabled_setting_file_path, "r") as filestream:
            for line in filestream:
                if line.strip()==self.__setting_for_is_enabled:
                    self.__is_enabled = True
                    return
            self.__is_enabled = False

    
    def __store_is_enabled_in_file(self):
        """
        Helper method to store the is_enabled setting to a file.

        If we store the setting as enabled, save the __setting_for_is_enabled string value
        in the file. If we are storing the value as disabled, remove this string from the file.
        """
        if self.__is_enabled:
            # add string to file
            with open(self.__is_enabled_setting_file_path, "a") as filestream:
                print(self.__setting_for_is_enabled)
                print("storing to file")
                filestream.write("\n"+self.__setting_for_is_enabled.strip())
        else:
            # rm string from file
            # read whole file, skip the setting
            new_file_text_lst = []
            with open(self.__is_enabled_setting_file_path, "r") as filestream:
                for line in filestream:
                    if line.strip()!=self.__setting_for_is_enabled:
                        new_file_text_lst.append(line.strip())
            with open(self.__is_enabled_setting_file_path, "w") as filestream:
                # write back everything that was read, except the setting since we skipped that
                filestream.write("\n".join(new_file_text_lst))