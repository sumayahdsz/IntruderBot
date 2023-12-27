from intruderDetector import IntruderDetector
import cv2
import numpy as np
import tkinter as tk
from tkinter import filedialog
import tkinter.scrolledtext as st
import tkinter.font as tkFont
from PIL import Image, ImageTk
from threading import Thread, Lock
import queue
import os
from os import startfile
from audioNotifier import AudioNotifier, IntruderInfo
from emailNotifier import EmailNotifier
from phoneNotifier import PhoneNotifier
from visualNotifier import VisualNotifier
from datetime import datetime
from myColours import MY_COLOURS
import shutil
import re
from enum import Enum


lock = Lock()
# example path: 'C:/Users/mcd_s/Desktop/proj/'
project_path = os.getcwd().replace("\\", "/")+"/"
live_photos_path=project_path+'livePhotos'
training_images_path=project_path+'images/training'
file_with_intruder_threshold=project_path+'configs/intruderThreshold.txt'
notifiers_enabled_file_path=project_path+'configs/notifiersEnabled.txt'
audio_notifier_path=project_path+'configs/audioNotifierData.txt'
email_notifier_path=project_path+'configs/emailNotifierData.txt'
phone_notifier_path=project_path+'configs/phoneNotifierData.txt'
visual_notifier_loc, audio_notifier_loc, email_notifier_loc, phone_notifier_loc = 0, 1, 2, 3
intruder_bot_image=project_path+"images/intruderbotlogo.jpg"
notifiers_list = [] # kept as a global var since app depends on notifiers, and notifiers depends on app (for the visual notifier)

# using re.compile() and saving the result is more efficient than calling re.match with the uncompiled pattern multiple times
# phone number pattern
phone_number_validation_pattern = "\s*\\+?[1-9][0-9]{7,14}\s*"
phone_number_validation_compiled = re.compile(phone_number_validation_pattern)

# email pattern
email_validation_pattern = "\s*\S+@\S+\.\S+\s*"
email_validation_compiled = re.compile(email_validation_pattern)


class DuplicateUserWindow:
    '''This window is used to help a user decide what to do when there is a duplicate user'''

    # Set of actions:
    ## DELETE_OLD - Delete pre-existing user and continue with creation of new user
    ## CANCEL_NEW - Keep pre-existing user and stop creation of new user
    ## KEEP_BOTH - Keep both old user and new user. Proceed with creation of new user
    Action = Enum('Action', ['DELETE_OLD', 'CANCEL_NEW', 'KEEP_BOTH'])

    def __init__(self, root, next_action, was_old_user_intruder):
        # Init Windown
        # next action is a list. It helps tell the window that launched this window what action to take next

        # setting title
        root.title("Duplicate User")
        # save variables as part of this object
        self.root = root
        self.next_action = next_action
        # Set command for the red cross on the top right
        root.protocol("WM_DELETE_WINDOW", lambda: close_window(self.root))
        


        # setting window size
        width=687
        height=432
        screenwidth = root.winfo_screenwidth()
        screenheight = root.winfo_screenheight()
        alignstr = '%dx%d+%d+%d' % (width, height, (screenwidth - width) / 2, (screenheight - height) / 2)
        root.geometry(alignstr)
        root.resizable(width=False, height=False)

        # Fonts
        ft_20 = tkFont.Font(family='Times',size=20)
        ft_22 = tkFont.Font(family='Times',size=22)
        
        # Set up keep both users button
        keep_both_users_button=tk.Button(root)
        keep_both_users_button["bg"] = MY_COLOURS["bumble_yellow"]
        keep_both_users_button["font"] = ft_20
        keep_both_users_button["fg"] = MY_COLOURS["black"]
        keep_both_users_button["justify"] = "center"
        keep_both_users_button["text"] = "Keep Pre-existing User and New User"
        keep_both_users_button.place(x=10,y=140,width=650,height=64)
        keep_both_users_button["command"] = lambda: self.save_action_and_close_window(DuplicateUserWindow.Action["KEEP_BOTH"])
        
        # Set up user already exists label
        user_already_exists_label=tk.Label(root)
        user_already_exists_label["font"] = ft_20
        user_already_exists_label["fg"] = MY_COLOURS["dark_grey"]
        user_already_exists_label["justify"] = "center"
        user_already_exists_label["text"] = "User Already Exists, but is " + ("not " if was_old_user_intruder else "") + "an intruder."
        user_already_exists_label.place(x=10,y=40,width=650,height=64)

        # Delete old user button
        delete_old_user_button=tk.Button(root)
        delete_old_user_button["bg"] = MY_COLOURS["pinkish_red"]
        delete_old_user_button["font"] = ft_20
        delete_old_user_button["fg"] = MY_COLOURS["black"]
        delete_old_user_button["justify"] = "center"
        delete_old_user_button["text"] = "Delete Pre-existing User"
        delete_old_user_button.place(x=10,y=210,width=650,height=64)
        delete_old_user_button["command"] = lambda: self.save_action_and_close_window(DuplicateUserWindow.Action["DELETE_OLD"])

        # Cancel creating new user button
        cancel_creating_new_user_button=tk.Button(root)
        cancel_creating_new_user_button["bg"] = MY_COLOURS["dark_red"]
        cancel_creating_new_user_button["font"] = ft_20
        cancel_creating_new_user_button["fg"] = MY_COLOURS["black"]
        cancel_creating_new_user_button["justify"] = "center"
        cancel_creating_new_user_button["text"] = "Cancel Adding New User"
        cancel_creating_new_user_button.place(x=10,y=280,width=650,height=64)
        cancel_creating_new_user_button["command"] = lambda: self.save_action_and_close_window(DuplicateUserWindow.Action["CANCEL_NEW"])
    

    def save_action_and_close_window(self, action: Action) -> None:
        # Save action to next_action list and close window
        # RETURNS None
        self.next_action.append(action)
        close_window(self.root)


class AddUserWindow:
    def __init__(self, root, model):
        #setting title
        self.root = root
        root.title("Add User")
        self.model = model

        #setting window size
        width=898
        height=492
        screenwidth = root.winfo_screenwidth()
        screenheight = root.winfo_screenheight()
        alignstr = '%dx%d+%d+%d' % (width, height, (screenwidth - width) / 2, (screenheight - height) / 2)
        root.geometry(alignstr)
        root.resizable(width=False, height=False)
        
        # fonts
        ft_20 = tkFont.Font(family='Times',size=20)
        ft_22 = tkFont.Font(family='Times',size=22)

        # upload user images button
        upload_user_images_button=tk.Button(root)
        upload_user_images_button["bg"] = MY_COLOURS["light_blue"]
        upload_user_images_button["font"] = ft_20
        upload_user_images_button["fg"] = MY_COLOURS["black"]
        upload_user_images_button["justify"] = "center"
        upload_user_images_button["text"] = "Upload User Images"
        upload_user_images_button.place(x=460,y=150,width=409,height=68)
        upload_user_images_button["command"] = self.upload_user_images_command

        # user name entry
        self.user_name_entry=tk.Entry(root)
        self.user_name_entry["borderwidth"] = "1px"
        self.user_name_entry["font"] = ft_22
        self.user_name_entry["fg"] = MY_COLOURS["dark_grey"]
        self.user_name_entry["justify"] = "center"
        self.user_name_entry["text"] = "enter user name"
        self.user_name_entry["relief"] = "sunken"
        self.user_name_entry.place(x=340,y=40,width=532,height=41)

        # user name label
        user_name_label=tk.Label(root)
        user_name_label["font"] = ft_22
        user_name_label["fg"] = MY_COLOURS["dark_grey"]
        user_name_label["justify"] = "left"
        user_name_label["text"] = "User Name"
        user_name_label.place(x=30,y=40,width=257,height=44)

        # open user images button
        open_user_images_button=tk.Button(root)
        open_user_images_button["bg"] = MY_COLOURS["light_blue"]
        open_user_images_button["font"] = ft_22
        open_user_images_button["fg"] = MY_COLOURS["black"]
        open_user_images_button["justify"] = "center"
        open_user_images_button["text"] = "Open User Images"
        open_user_images_button.place(x=20,y=150,width=412,height=68)
        open_user_images_button["command"] = self.open_user_imgs_command

        # Check box to indicate whether user being added is an intruder or not
        self.is_intruder = tk.IntVar()
        self.is_intruder.set(0)
        self.is_intruder_checkbox=tk.Checkbutton(root, text="Is Intruder", width=350, height=30, variable=self.is_intruder, onvalue=1, offvalue=0,  command=self.is_intruder_command)
        self.is_intruder_checkbox["font"] = ft_22
        self.is_intruder_checkbox["fg"] = MY_COLOURS["dark_grey"]
        self.is_intruder_checkbox["justify"] = "left"
        self.is_intruder_checkbox.place(x=30,y=100,width=303,height=37)

        # ScrolledText to communicate any successful or erroneous user additions/deletions 
        self.upload_message_text=st.ScrolledText(root)
        self.upload_message_text.configure(state='normal')
        self.upload_message_text.config(foreground=MY_COLOURS["light_green"], background=MY_COLOURS["black"], font=ft_22) 
        self.upload_message_text.place(x=90,y=320,width=705,height=87)
        self.upload_message_text.insert(tk.INSERT, "Message: Upload Successful", ("centered",))
        self.upload_message_text.tag_configure("centered", justify="center")
        self.upload_message_text.configure(state='disabled')

        # Save and close button
        save_and_close_button=tk.Button(root)
        save_and_close_button["bg"] = MY_COLOURS["pinkish_red"]
        save_and_close_button["font"] = ft_22
        save_and_close_button["fg"] = MY_COLOURS["black"]
        save_and_close_button["justify"] = "center"
        save_and_close_button["text"] = "Save & Close"
        save_and_close_button.place(x=520,y=420,width=347,height=59)
        save_and_close_button["command"] = self.save_and_close_command

        # Delete user button
        delete_user_button=tk.Button(root)
        delete_user_button["bg"] = MY_COLOURS["pinkish_red"]
        delete_user_button["font"] = ft_22
        delete_user_button["fg"] = MY_COLOURS["black"]
        delete_user_button["justify"] = "center"
        delete_user_button["text"] = "Delete User"
        delete_user_button.place(x=340,y=240,width=215,height=67)
        delete_user_button["command"] = self.delete_user_command

        # display gui components and make them active
        root.mainloop()
    
    def user_exists(self):
        # check if the user already exists
        is_intruder = self.is_intruder.get()
        folder_path = self.__construct_user_folder_path(is_intruder)
        # return true if user exists, else false
        return os.path.exists(folder_path) 

    def __construct_user_folder_path(self, is_intruder):
        # helper function to contruct a file path given a particular user name and whether they are an intruder or not
        # returns the constructed file path as a string

        # remove white space from user name and make user name lower case. Also remove all new line characters
        user_name = self.user_name_entry.get().strip().lower().replace("\n", "")
        
        folder_path = training_images_path + "/" + user_name + f'{"__intruder" if is_intruder else "__safe"}'
        return folder_path
    
    def check_if_alternate_user_saved(self):
        # checks if the user already exists, but is saved as the other kind (intruder as safe / safe as intruder)
        # If user exists as the other kind, returns a tuple of action selected from the popup window (Duplicate User Window) and path of already exisiting user folder
        # If user does not exist as the other kind, returns a tuple of None (no action) and path that the other kind would have had
        is_intruder = self.is_intruder.get()
        path_to_check = self.__construct_user_folder_path(not is_intruder)
        if (os.path.exists(path_to_check)):
            # user exists, but as the opposite type
            self.duplicateUserWindow = tk.Toplevel(self.root)
            self.action_on_duplicate_user_window_close = []
            # duplicate user window launches a new window. The action that the user selects from this window is saved in action_on_duplicate_user_window_close
            DuplicateUserWindow(self.duplicateUserWindow, self.action_on_duplicate_user_window_close, is_intruder)
            # Wait for previous window to close before proceeding
            self.root.wait_window(self.duplicateUserWindow)
            return self.action_on_duplicate_user_window_close[0], path_to_check
        # User doesn't exist as the opposite type
        return None, path_to_check
    
    def __upload_msg_callback(self, is_user_exists):
        # function that is called to update the upload message label when there is a successful upload

        # check that the window exists before updating it, else we will have a race case an potentially access memory we dont own on this thread
        if self.root:
            self.upload_message_text.configure(state='normal')
            self.upload_message_text.delete('1.0', tk.END)
            self.upload_message_text.config(foreground=MY_COLOURS["light_green"], background=MY_COLOURS["black"]) 
            self.upload_message_text.insert(tk.INSERT, "Exisiting user updated successfully" if is_user_exists else "New user added successfully", ("centered",))
            self.upload_message_text.configure(state='disabled')
        

    def upload_user_images_command(self):
        # subroutine to upload user images
        # returns None

        # get user name and whether is intruder is selected
        user_name = self.user_name_entry.get().strip()
        if not user_name:
            # if user name is blank
            self.upload_message_text.configure(state='normal')
            self.upload_message_text.delete('1.0', tk.END)
            self.upload_message_text.config(foreground='red', background=MY_COLOURS["black"]) 
            self.upload_message_text.insert(tk.INSERT, "Please enter a non-empty user name", ("centered",))
            self.upload_message_text.configure(state='disabled')
            return
        is_intruder = self.is_intruder.get()
        # contruct folder path
        user_file_path = self.__construct_user_folder_path(is_intruder)
        # check if user exists
        is_user_exists = self.user_exists()
        # check if user exists but as the opposite type (trying to create a new user as safe, but there is an intruder with the same name - or vice versa)
        action, path_to_check = self.check_if_alternate_user_saved()

        if action == DuplicateUserWindow.Action.CANCEL_NEW:
            # if cancel creating new user, dont do anything
            self.upload_message_text.configure(state='normal')
            self.upload_message_text.delete('1.0', tk.END)
            self.upload_message_text.config(foreground=MY_COLOURS["pinkish_red"], background=MY_COLOURS["black"]) 
            self.upload_message_text.insert(tk.INSERT, "New user not created due to duplicate", ("centered",))
            self.upload_message_text.configure(state='disabled')
            return
        elif action == DuplicateUserWindow.Action.DELETE_OLD:
            # delete other directory (pre-existing user) and continue with the alternative
            shutil.rmtree(path_to_check)

        # if action was None or KEEP_BOTH, we proceed as usual with creation

        if not is_user_exists:
            # create user directory if it didn't already exist
            mode = 0o666
            os.mkdir(user_file_path, mode)

        # Populate message to indicate what user should do to upload images
        self.upload_message_text.configure(state='normal')
        self.upload_message_text.delete('1.0', tk.END)
        self.upload_message_text.config(foreground=MY_COLOURS["bumble_yellow"], background=MY_COLOURS["black"])
        self.upload_message_text.insert(tk.INSERT, f'Select {"additional " if is_user_exists else ""}images to identify {user_name}. Hold Ctrl to select multiple pictures.', ("centered",))
        self.upload_message_text.configure(state='disabled')
        # launch window to open files
        f_types = [('Jpg Files', '*.jpg'),
            ('PNG Files','*.png')]   # type of files to select 
        files_to_copy = tk.filedialog.askopenfilename(multiple=True,filetypes=f_types)
        for file_to_copy in files_to_copy:
            # save file to the user directory
            shutil.copy(file_to_copy, user_file_path)
        
        # populate message to tell the user to wait
        self.upload_message_text.configure(state='normal')
        self.upload_message_text.delete('1.0', tk.END)
        self.upload_message_text.config(foreground=MY_COLOURS["bumble_yellow"], background=MY_COLOURS["black"])
        self.upload_message_text.insert(tk.INSERT, "Updating program with new images. Please wait", ("centered",))
        self.upload_message_text.configure(state='disabled')
        #self.upload_message_label["text"] = "Updating program with new images. Please wait."
        
        # retrain model on a new thread, in parallel, so that user doesn't need to have the gui frozen while the model is retrained with the new images
        model_thread = Thread(target = lambda : self.model.train_model() or self.__upload_msg_callback(is_user_exists), args = ())
        model_thread.start()
        

    def open_user_imgs_command(self):
        # launch a window with the folder of images used for the user
        # RETURNS None
        



















        # remove whitespace for the user name
        user_name = self.user_name_entry.get().strip()
        # check whether is_intruder is selected
        is_intruder = self.is_intruder.get()
        if not user_name:
            # if user name is blank, prompt user to enter a user name
            self.upload_message_text.configure(state='normal')
            self.upload_message_text.delete('1.0', tk.END)
            self.upload_message_text.config(foreground='red', background=MY_COLOURS["black"])
            self.upload_message_text.insert(tk.INSERT, "Please enter a user name.", ("centered",))
            self.upload_message_text.configure(state='disabled')
            #self.upload_message_label["text"] = "Please enter a user name."
            return
        
        # check if user already exists
        is_user_exists = self.user_exists()

        if not is_user_exists:
            # if user doesn't exist, don't open directory
            self.upload_message_text.configure(state='normal')
            self.upload_message_text.delete('1.0', tk.END)
            self.upload_message_text.config(foreground='red', background=MY_COLOURS["black"])
            self.upload_message_text.insert(tk.INSERT, f"User doesn't exist as {'intruder' if self.is_intruder.get() else 'non-intruder'}.", ("centered",))
            self.upload_message_text.configure(state='disabled')
            #self.upload_message_label["text"] = f"User doesn't exist as {'intruder' if self.is_intruder.get() else 'non-intruder'}."
            return
        
        # Open folder for user
        user_file_path = self.__construct_user_folder_path(is_intruder)
        os.startfile(user_file_path)


    def is_intruder_command(self):
        # don't do anything when the is_intruder checkbox is ticked/unticked
        # the value will only be read when a user is added/deleted/modified
        pass
    

    def save_and_close_command(self):
        # close window (saving is automatically done when user clicks other buttons)
        # this is why there is no second option to only close the window
        close_window(self.root)


    def delete_user_command(self):
        # Deletes a user directory
        if not self.user_exists():
            # Deleting a non-existing user is not possible, so we tell the user this
            self.upload_message_text.configure(state='normal')
            self.upload_message_text.delete('1.0', tk.END)
            self.upload_message_text.config(foreground='red', background=MY_COLOURS["black"])
            self.upload_message_text.insert(tk.INSERT, f"User doesn't exist as {'intruder' if self.is_intruder.get() else 'non-intruder'}.", ("centered",))
            self.upload_message_text.configure(state='disabled')
            #self.upload_message_label["text"] = f"User doesn't exist as {'intruder' if self.is_intruder.get() else 'non-intruder'}."
            return
        # else - delete the user, after confirming with user that they want to delete the user

        is_delete_user_confirmed = tk.messagebox.askyesno(title='confirmation',
                    message='Are you sure that you want to delete the user?')
        if is_delete_user_confirmed:
            # delete the user
            # check whether is_intruder is selected
            is_intruder = self.is_intruder.get()
            shutil.rmtree(self.__construct_user_folder_path(is_intruder))
            self.upload_message_text.configure(state='normal')
            self.upload_message_text.delete('1.0', tk.END)
            self.upload_message_text.config(foreground=MY_COLOURS["light_green"], background=MY_COLOURS["black"])
            self.upload_message_text.insert(tk.INSERT, f"User Deleted", ("centered",))
            self.upload_message_text.configure(state='disabled')
            return
        self.upload_message_text.configure(state='normal')
        self.upload_message_text.delete('1.0', tk.END)
        self.upload_message_text.config(foreground='red', background=MY_COLOURS["black"])
        self.upload_message_text.insert(tk.INSERT, f"User deletion cancelled. User still exists.", ("centered",))
        self.upload_message_text.configure(state='disabled')
    

class ConfigWindow:
    def __init__(self, root, model):
        #setting title
        root.title("Configure")
        self.root = root
        self.model = model

        #setting window size
        width=1104
        height=745
        screenwidth = root.winfo_screenwidth()
        screenheight = root.winfo_screenheight()
        alignstr = '%dx%d+%d+%d' % (width, height, (screenwidth - width) / 2, (screenheight - height) / 2)
        root.geometry(alignstr)
        root.resizable(width=False, height=False)

        # Create fonts
        ft_22 = tkFont.Font(family='Times',size=22)
        ft_14 = tkFont.Font(family='Times',size=14)
        
        # Button layout and functionality for add/edit user images button
        add_user_button=tk.Button(root)
        add_user_button["activebackground"] = MY_COLOURS["light_blue"]
        add_user_button["anchor"] = "nw"
        add_user_button["bg"] = MY_COLOURS["black"]
        add_user_button["font"] = ft_22

        add_user_button["fg"] = MY_COLOURS["light_blue"]
        add_user_button["justify"] = "center"
        add_user_button["text"] = "Add/Edit User Images"
        add_user_button["relief"] = "raised"
        add_user_button.place(x=30,y=120,width=331,height=59)
        add_user_button["command"] = self.launch_add_user_window


        # Button layout and functionality for "save and close" button
        save_and_close_button=tk.Button(root)
        save_and_close_button["bg"] = MY_COLOURS["light_blue"]
        save_and_close_button["font"] = ft_22
        save_and_close_button["fg"] = MY_COLOURS["black"]
        save_and_close_button["justify"] = "center"
        save_and_close_button["text"] = "Save & Close"
        save_and_close_button["relief"] = "raised"
        save_and_close_button.place(x=30,y=660,width=291,height=61)
        save_and_close_button["command"] = self.save_settings_and_close_window_command

        # Button layout and functionality for "discard changes" button
        discard_changes_button=tk.Button(root)
        discard_changes_button["activeforeground"] = MY_COLOURS["dark_red"]
        discard_changes_button["bg"] = MY_COLOURS["dark_red"]
        discard_changes_button["font"] = ft_22
        discard_changes_button["fg"] = MY_COLOURS["white"]
        discard_changes_button["justify"] = "center"
        discard_changes_button["text"] = "Discard Changes"
        discard_changes_button.place(x=780,y=660,width=297,height=63)
        discard_changes_button["command"] = self.close_without_save_command

        # Button layout and functionality for "test sound" button
        test_sound_button=tk.Button(root)
        test_sound_button["bg"] = MY_COLOURS["black"]
        test_sound_button["font"] = ft_22
        test_sound_button["fg"] = MY_COLOURS["light_blue"]
        test_sound_button["justify"] = "center"
        test_sound_button["text"] = "Test Sound"
        test_sound_button["relief"] = "flat"
        test_sound_button.place(x=350,y=400,width=192,height=40)
        test_sound_button["command"] = self.test_sound

        # Label layout for "Image detection settings" label
        image_detection_settings_label=tk.Label(root)
        image_detection_settings_label["font"] = ft_22
        image_detection_settings_label["fg"] = MY_COLOURS["black"]
        image_detection_settings_label["justify"] = "left"
        image_detection_settings_label["text"] = "Image Detection Settings:"
        image_detection_settings_label.place(x=0,y=20,width=451,height=39)

        # Page divider label for aesthetic purposes as well as screen readabilty
        page_divider_label=tk.Label(root)
        page_divider_label["font"] = ft_22
        page_divider_label["fg"] = MY_COLOURS["light_blue"]
        page_divider_label["justify"] = "center"
        page_divider_label["text"] = "₊˚ ✧ ‿︵‿୨୧‿︵‿ ✧ ₊˚"
        page_divider_label.place(x=0,y=180,width=1091,height=38)

        # Label layout for "Intruder Threshold" label
        intruder_threshold_label=tk.Label(root)
        intruder_threshold_label["font"] = ft_22
        intruder_threshold_label["fg"] = MY_COLOURS["dark_grey"]
        intruder_threshold_label["justify"] = "left"
        intruder_threshold_label["text"] = "Intruder Threshold"
        intruder_threshold_label.place(x=30,y=70,width=301,height=30)

        # threshold info input entry
        self.threshold_info=tk.Entry(root, font=14)
        self.threshold_info["borderwidth"] = "4px"
        self.threshold_info["font"] = ft_14
        self.threshold_info["fg"] = MY_COLOURS["dark_grey"]
        self.threshold_info["justify"] = "center"
        self.txt=self.model.get_is_intruder_threshold()
        print(self.txt)
        print("thresholddd")
        self.threshold_info.delete(0,tk.END)
        self.threshold_info.insert(0,self.txt)
        self.threshold_info.place(x=480,y=70,width=101,height=30)

        # Notifications settings label
        notifications_settings_label=tk.Label(root)
        notifications_settings_label["font"] = ft_22
        notifications_settings_label["fg"] = MY_COLOURS["black"]
        notifications_settings_label["justify"] = "left"
        notifications_settings_label["text"] = "Notification Settings:"
        notifications_settings_label.place(x=0,y=230,width=350,height=30)

        # Email list label
        email_list_label=tk.Label(root)
        email_list_label["font"] = ft_22
        email_list_label["fg"] = MY_COLOURS["dark_grey"]
        email_list_label["justify"] = "left"
        email_list_label["text"] = "Email List"
        email_list_label.place(x=30,y=500,width=308,height=46)

        # Audio alert enabled checkbox
        self.audio_alert_enabled = tk.IntVar()
        self.audio_alert_enabled.set(notifiers_list[audio_notifier_loc].get_enabled())
        self.GCheckBox_audio_alert=tk.Checkbutton(root, text="Enable Audio Alert", width=350, height=30, variable=self.audio_alert_enabled, onvalue=1, offvalue=0,  command=self.toggle_audio_alert_enabled) #image=phoImage,
        self.GCheckBox_audio_alert["font"] = ft_22
        self.GCheckBox_audio_alert["fg"] = MY_COLOURS["dark_grey"]
        self.GCheckBox_audio_alert["justify"] = "left"
        self.GCheckBox_audio_alert.place(x=30,y=280,width=350,height=32)

        # audio file path entry
        self.audio_file_path=tk.Entry(root, font=14)
        self.audio_file_path["borderwidth"] = "4px"
        self.audio_file_path["font"] = ft_14
        self.audio_file_path["fg"] = MY_COLOURS["dark_grey"]
        self.audio_file_path["justify"] = "left"
        audio_path_list=notifiers_list[audio_notifier_loc].get_data_list()
        self.txt = audio_path_list[0] if audio_path_list else ""
        self.audio_file_path.delete(0,tk.END)
        self.audio_file_path.insert(0,self.txt)
        self.audio_file_path.place(x=50,y=360,width=492,height=30)

        # Audio file path label
        audio_file_path_label=tk.Label(root)
        audio_file_path_label["font"] = ft_22
        audio_file_path_label["fg"] = MY_COLOURS["dark_grey"]
        audio_file_path_label["justify"] = "left"
        audio_file_path_label["text"] = "Audio File Path"
        audio_file_path_label.place(x=30,y=320,width=325,height=30)

        # Select file button (For audio)
        select_audio_file_button=tk.Button(root)
        select_audio_file_button["bg"] = MY_COLOURS["black"]
        select_audio_file_button["font"] = ft_22
        select_audio_file_button["fg"] = MY_COLOURS["light_blue"]
        select_audio_file_button["justify"] = "center"
        select_audio_file_button["text"] = "Select File"
        select_audio_file_button.place(x=120,y=400,width=192,height=40)
        select_audio_file_button["command"] = self.browse_files_for_audio_path

        # Enable email alerts checkbox
        self.email_alert_enabled_int = tk.IntVar()
        self.email_alert_enabled_int.set(notifiers_list[email_notifier_loc].get_enabled())
        self.email_alert_enabled_checkbox=tk.Checkbutton(root, text="Enable Email Alerts", width=350, height=100, variable=self.email_alert_enabled_int, onvalue=1, offvalue=0,  command=self.toggle_email_alert_enabled)
        self.email_alert_enabled_checkbox["font"] = ft_22
        self.email_alert_enabled_checkbox["fg"] = MY_COLOURS["dark_grey"]
        self.email_alert_enabled_checkbox["justify"] = "left"
        self.email_alert_enabled_checkbox.place(x=30,y=460,width=350,height=100)
        
        # Email scrollable input entry
        self.email_scroll_text=st.ScrolledText(root)
        self.email_scroll_text.place(x=50,y=550,width=492,height=74)
        self.email_scroll_text.insert(tk.INSERT, "\n".join(notifiers_list[email_notifier_loc].get_data_list())) 

        # Phone alert checkbox
        self.phone_alert_enabled_int = tk.IntVar()
        self.phone_alert_enabled_int.set(notifiers_list[phone_notifier_loc].get_enabled())
        self.phone_alert_enabled_checkbox=tk.Checkbutton(root, text="Enable Phone Alerts", width=350, height=100, variable=self.phone_alert_enabled_int, onvalue=1, offvalue=0,  command=self.toggle_phone_alert_enabled)
        self.phone_alert_enabled_checkbox["font"] = ft_22
        self.phone_alert_enabled_checkbox["fg"] = MY_COLOURS["dark_grey"]
        self.phone_alert_enabled_checkbox["justify"] = "left"
        self.phone_alert_enabled_checkbox.place(x=600,y=230,width=350,height=100)

        # phone numbers list label
        phone_numbers_list_label=tk.Label(root)
        phone_numbers_list_label["font"] = ft_22
        phone_numbers_list_label["fg"] = MY_COLOURS["dark_grey"]
        phone_numbers_list_label["justify"] = "left"
        phone_numbers_list_label["text"] = "Phone Numbers List"
        phone_numbers_list_label.place(x=640,y=320,width=313,height=30)

        # Phone number scrollable entry
        self.phone_scroll_text=st.ScrolledText(root)
        self.phone_scroll_text.place(x=640,y=360,width=438,height=127)
        self.phone_scroll_text.insert(tk.INSERT, "\n".join(notifiers_list[phone_notifier_loc].get_data_list()))


    def launch_add_user_window(self):
        # Launches a window so that users can be added/deleted/modified
        self.configureWindow = tk.Toplevel(self.root)
        AddUserWindow(self.configureWindow, self.model)

    @classmethod
    def input_regex_checker_has_error(cls, all_strs, compiled_pattern, error_msg, popup_title):
        # return true if there is an error with the data_list not matching what is in the compiled pattern.
        # Also displays a pop up window with the error
        #all_strs = " ".join(data_list)
        # replace all phone numbers with nothing and then remove all white space
        new_phone_str = re.sub(compiled_pattern, "", all_strs).strip()
        # if there is anything left, there is an issue
        if new_phone_str:
            message = error_msg.format(new_phone_str)
            tk.messagebox.showerror(title=popup_title, message=message)
            return True
        return False


    def save_settings_and_close_window_command(self):
        # save all text values and then close the window

        # save each phone number
        phone_nums = self.phone_scroll_text.get("1.0", tk.END)
        # use a regex check to ensure each phone number is only + signs and/or digits
        has_error = ConfigWindow.input_regex_checker_has_error(phone_nums, phone_number_validation_compiled, "Phone number should not contain '{}'. Please include only + and digits in the number.", "Phone Number Error")
        if has_error:
            return
        
        # save each email address
        emails = self.email_scroll_text.get("1.0", tk.END)
        has_error = ConfigWindow.input_regex_checker_has_error(emails, email_validation_compiled, "Email format invalid '{}'.", "Email Address Error")
        if has_error:
            return
        

        # save threshold
        threshold = self.threshold_info.get().strip()
        try:
            threshold_float = float(threshold) # can throw value error if can't convert to float
            if threshold_float > 1 or threshold_float < 0:
                raise ValueError("Please enter a decimal threshold between 0 and 1")
        except ValueError:
            tk.messagebox.showerror(title="Threshold input error", message="Please enter a decimal threshold between 0 and 1")
            return
        
        # Save all values
        self.model.set_is_intruder_threshold(threshold)
        notifiers_list[phone_notifier_loc].set_data_list(phone_nums.splitlines())
        notifiers_list[email_notifier_loc].set_data_list(emails.splitlines())
        # save audio sound file path
        # No regex check since users select this by clicking a file usually
        notifiers_list[audio_notifier_loc].set_data_list([self.audio_file_path.get().strip()])

        # close the configure window
        close_window(self.root)


    def close_without_save_command(self):
        # Close the config window without saving configs.
        close_window(self.root)


    def test_sound(self):
        # Triggered when the test sound button is clicked
        # plays the audio whose path is written out on the gui so that the user can test the sound
        AudioNotifier.play_audio_with_error_check(self.audio_file_path.get())


    def toggle_audio_alert_enabled(self):
        # Triggered when the checkbox to enable/disable the audio notifier is clicked. 
        # Is used to enable/disable the audio notifier.
        notifiers_list[audio_notifier_loc].set_enabled(not notifiers_list[audio_notifier_loc].get_enabled())


    def browse_files_for_audio_path(self):
        # Opens a window that lets users pick an audio file
        filename = filedialog.askopenfilename(filetypes=(("mp3 audio files","*.mp3"),("All files","*.*")))
        if filename:
            # if the user picks a file, the gui label is updated to contain the new file path
            self.audio_file_path.delete(0, tk.END)
            self.audio_file_path.insert(tk.END, filename)


    def toggle_email_alert_enabled(self):
        # Triggered when the checkbox to enable/disable the email notifier is clicked. 
        # Is used to enable/disable the email notifier.
        notifiers_list[email_notifier_loc].set_enabled(not notifiers_list[email_notifier_loc].get_enabled())


    def toggle_phone_alert_enabled(self):
        # Triggered when the checkbox to enable/disable the phone notifier is clicked. 
        # Is used to enable/disable the phone notifier.
        notifiers_list[phone_notifier_loc].set_enabled(not notifiers_list[phone_notifier_loc].get_enabled())
        

class App:
    # Gui for the main window
    def __init__(self, root, video, model, thread_queue):
        # initialize resources
        self.video = video
        self.model = model
        self.thread_queue = thread_queue
        #setting window title
        root.title("IntruderBot")
        #setting window size
        width=940
        height=583

        # create video widget on the right
        screenwidth = root.winfo_screenwidth()
        screenheight = root.winfo_screenheight()
        alignstr = '%dx%d+%d+%d' % (width, height, (screenwidth - width) / 2, (screenheight - height) / 2)
        root.geometry(alignstr)
        root.resizable(width=False, height=False)

        # defining fonts (size 22 and 18 for clear visibility)
        ft_22 = tkFont.Font(family='Times',size=22)
        ft_18 = tkFont.Font(family='Times',size=18)

        # Help button
        help_button_main=tk.Button(root)
        help_button_main["activebackground"] = MY_COLOURS["dark_grey"]
        help_button_main["anchor"] = "center"
        help_button_main["bg"] = MY_COLOURS["light_blue"]
        ft = tkFont.Font(family='Times',size=22)
        help_button_main["font"] = ft
        help_button_main["fg"] = MY_COLOURS["black"]
        help_button_main["justify"] = "center"
        help_button_main["text"] = "Help"
        help_button_main["relief"] = "raised"
        help_button_main.place(x=30,y=30,width=534,height=71)
        help_button_main["command"] = self.help_button_command

        # configure button
        configure_button_main=tk.Button(root)
        configure_button_main["bg"] = MY_COLOURS["black"]
        configure_button_main["font"] = ft_22
        configure_button_main["fg"] = MY_COLOURS["light_blue"]
        configure_button_main["justify"] = "center"
        configure_button_main["text"] = "Configure"
        configure_button_main["relief"] = "flat"
        configure_button_main.place(x=30,y=120,width=532,height=74)
        configure_button_main["command"] = self.launch_config_window_command

        # label to indicate if intruder or not (changes color from green to red on intruder detection)
        self.GLabel_is_intruder_detected=tk.Label(root)
        self.GLabel_is_intruder_detected["activebackground"] = "#90ee90"
        self.GLabel_is_intruder_detected["activeforeground"] = "#90ee90"
        self.GLabel_is_intruder_detected["bg"] = "#90ee90"
        self.GLabel_is_intruder_detected["font"] = ft_18
        self.GLabel_is_intruder_detected["fg"] = MY_COLOURS["dark_grey"]
        self.GLabel_is_intruder_detected["justify"] = "center"
        self.GLabel_is_intruder_detected["text"] = "No intruder detected"
        self.GLabel_is_intruder_detected["relief"] = "sunken"
        self.GLabel_is_intruder_detected.place(x=30,y=300,width=538,height=66)

        # exit button on bottom right
        close_button_main=tk.Button(root)
        close_button_main["activeforeground"] = MY_COLOURS["dark_red"]
        close_button_main["bg"] = MY_COLOURS["dark_red"]
        close_button_main["font"] = ft_22
        close_button_main["fg"] = MY_COLOURS["white"]
        close_button_main["justify"] = "center"
        close_button_main["text"] = "Exit"
        close_button_main.place(x=630,y=500,width=297,height=63)
        close_button_main["command"] = self.close_window_command
        
        # open intruder images button
        open_intruder_imgs_button_main=tk.Button(root)
        open_intruder_imgs_button_main["bg"] = MY_COLOURS["black"]
        open_intruder_imgs_button_main["font"] = ft_22
        open_intruder_imgs_button_main["fg"] = MY_COLOURS["light_blue"]
        open_intruder_imgs_button_main["justify"] = "center"
        open_intruder_imgs_button_main["text"] = "View Intruder images"
        open_intruder_imgs_button_main["relief"] = "flat"
        open_intruder_imgs_button_main.place(x=30,y=210,width=532,height=68)
        open_intruder_imgs_button_main["command"] = self.open_intruder_imgs_command

        # Reset Intruder Detection Button
        reset_intruder_detection_button_main=tk.Button(root)
        reset_intruder_detection_button_main["bg"] = "#dc582a"
        reset_intruder_detection_button_main["font"] = ft_22
        reset_intruder_detection_button_main["fg"] = MY_COLOURS["white"]
        reset_intruder_detection_button_main["justify"] = "center"
        reset_intruder_detection_button_main["text"] = "Reset Intruder Detection"
        reset_intruder_detection_button_main["relief"] = "groove"
        reset_intruder_detection_button_main.place(x=30,y=380,width=539,height=72)
        reset_intruder_detection_button_main["command"] = lambda : self.reset_intruder_detection_command("No intruder detected", "#90ee90")

        # set default image of panel on the right so it shows something when no 
        # intruder detected
        self.default_image=intruder_bot_image
        image1 = Image.open(self.default_image)
        test = ImageTk.PhotoImage(image1)
        self.GLabel_intruder_img=tk.Label(root, image=test)
        self.GLabel_intruder_img.image = test
        self.GLabel_intruder_img.place(x=630,y=30,width=299,height=422)
        
        self.window = root

    def get_default_image(self):
        return self.default_image

    def help_button_command(self):
        # play help video
        startfile("images\helpButton.mp4")

    def launch_config_window_command(self):
        self.configureWindow = tk.Toplevel(self.window)
        ConfigWindow(self.configureWindow, self.model)

    def close_window_command(self):
        print("close window")
        close_window_and_release_video(self.window, self.video, self.thread_queue)


    def open_intruder_imgs_command(self):
        # Launches a window with all the intruder pictures that were previously captured
        os.startfile(live_photos_path)

    
    def reset_intruder_detection_command(self, text, primary_color):
        # This command is triggered when the reset button is clicked
        # it changes the visual layout of the gui to match that of no intruder detected so far
        self.set_intruder_image()
        self.GLabel_is_intruder_detected["activebackground"] = primary_color
        self.GLabel_is_intruder_detected["activeforeground"] = primary_color
        self.GLabel_is_intruder_detected["bg"] = primary_color
        self.GLabel_is_intruder_detected["text"] = text

    
    def set_intruder_image(self,image_path=None):
        # Sets the image of the intruder frame on the right
        if image_path is None:
            image_path=self.default_image
        if self.window:
            img = ImageTk.PhotoImage(Image.open(image_path))
            self.GLabel_intruder_img.configure(image=img)
            self.GLabel_intruder_img.image = img
    

        

def get_frame_with_motion(video, thread_queue, threshold_to_detect_motion=0.3):
    # return frame when there is motion in the video
    prev_pixel_avg = 0
    is_first_time = True
    while(thread_queue.qsize()==0):
        lock.acquire()
        # the following code needs to be atomic
        # if the program is closed before this section of code is hit,
        # we end up accessing invalid memory when we do video.read,
        # causing a crash
        if thread_queue.qsize()==0:
            _, frame = video.read()
            # make image greyscale for consistency and higher accuracy
            grey_image_vector = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        lock.release()
        # calculate avg number of changed pixels
        result = np.abs(np.mean(grey_image_vector) - prev_pixel_avg)
        #print(result)
        prev_pixel_avg= np.mean(grey_image_vector)
        # if number of changed pixels is larger than the thrshold for motion
        # we skip this ection if this is the first time we 're looking at a frame since 
        # there is no previous frame to compare to. 
        if not is_first_time and result > threshold_to_detect_motion and not is_first_time:
            # motion detected
            return frame
        # this is not the first this loop has been called,
        # so set this variable to false so that on the next loop iteration
        # we compare to the previous frame mean
        is_first_time = False

def close_window(window):
    print("destroy windows")
    window.destroy()

def release_video_resources(video):
    video.release()
    cv2.destroyAllWindows()

    

def close_window_and_release_video(window, video, thread_queue):
    lock.acquire()
    thread_queue.put("release")
    lock.release()
    close_window(window)
    release_video_resources(video)



def set_up_gui(video, model, thread_queue):
    window = tk.Tk()
    window.protocol("WM_DELETE_WINDOW", lambda: close_window_and_release_video(window, video, thread_queue))
    app = App(window, video, model, thread_queue)
    return window,app


def process_live_video(video, model, image_dim_width, image_dim_len, thread_queue):
    # process live video
    while True:
        frame = get_frame_with_motion(video, thread_queue)
        if frame is None:
            # gui was closed
            return
        human_readable_datetime = datetime.now().strftime('%d_%B__%I_%M_%S_%p')
        intruder_picture_file='livePhotos/'+ str(human_readable_datetime) +'.jpg'
        
        im = Image.fromarray(frame, 'RGB')
        im = im.resize((image_dim_width, image_dim_len))
        prediction, probability = model.classify(test_image=im)
        if model.is_intruder(prediction, probability):
            intruder_info = IntruderInfo(datetime.now(), project_path+intruder_picture_file, probability)

            # save file
            cv2.imwrite(intruder_picture_file, frame)
            model.trigger_notifiers(intruder_info)
            print("intruder detected!!")
        key = cv2.waitKey(20)
        if key == 27: # exit on ESC
            release_video_resources(video)
            break

def init_notifiers_list(app):
    visual_notifier = VisualNotifier(notifiers_enabled_file_path, app)
    audio_notifier = AudioNotifier(audio_notifier_path, notifiers_enabled_file_path)
    email_notifier = EmailNotifier(email_notifier_path, notifiers_enabled_file_path)
    phone_notifier = PhoneNotifier(phone_notifier_path, notifiers_enabled_file_path)
    return [visual_notifier, audio_notifier, email_notifier, phone_notifier]

def main():
    # Read config file
    

    image_dim_width = 128
    image_dim_len = 128

    # turn camera on
    # detect motion
    # if motion - classify
    video = cv2.VideoCapture(0)
    
    # test_image_path='/Users/mcd_s/Desktop/proj/images/validation/face4/3face4.jpg'
    thread_queue = queue.Queue()
    # train model
    model = IntruderDetector(training_images_path, file_with_intruder_threshold, notifiers_list=notifiers_list)
    gui_window, app = set_up_gui(video, model, thread_queue)

    # set notifiers
    notifiers_list.extend(init_notifiers_list(app))

    # PROCESS LIVE VIDEO
    live_video_process_thread = Thread(target = process_live_video, args = (video, model, image_dim_width, image_dim_len, thread_queue))
    live_video_process_thread.start()
    gui_window.mainloop()
    live_video_process_thread.join()
main()



