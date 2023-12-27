from notifier import Notifier, IntruderInfo
from playsound import playsound, PlaysoundException
import ctypes

class AudioNotifier(Notifier):
    """
    Notifier that alerts users using an audio sound (wav or mp3 format)
    """
    # data_list is used for audio file path that the user stores
    # it will only have 1 element
    # works with wav and mp3 files
    def __init__(self, path_of_file_with_audio_file_path, is_enabled_setting_file_path):
        setting_for_is_enabled = "AudioNotifierOn"
        super().__init__(path_of_file_with_audio_file_path, setting_for_is_enabled, is_enabled_setting_file_path)
    
    def notify(self, intruder_info:IntruderInfo):
        # Function called to play an audio
        if not self.get_enabled():
            return
        audio_file = self.get_data_list()[0]
        AudioNotifier.play_audio_with_error_check(audio_file)

    @classmethod
    def play_audio_with_error_check(cls, audio_file):
        # Helper function to play an audio. Does not check if notifier is enabled
        try:
            # try playing the file
            playsound(audio_file)
        except PlaysoundException as context:
            # error playing the file, so show popup
            if "Error 263" in str(context):
                ctypes.windll.user32.MessageBoxW(0, f"please check audio path and type. Only Wav and mp3 files supported.", "Audio Notification Error", 0)
            else:
                # Different error type (could be unsupported driver, etc.)
                # most likely to happen only on the very first time the program runs, if at all this error occurs
                ctypes.windll.user32.MessageBoxW(0, f"{context}", "Audio Notification Error", 0)
