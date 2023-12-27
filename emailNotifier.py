from time import sleep
import tkinter
from notifier import Notifier, IntruderInfo
import os

from email import encoders
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import httplib2
from email.mime.image import MIMEImage
from oauth2client import client, tools, file
from apiclient import errors, discovery
import base64
from threading import Thread
# import time

class EmailNotifier(Notifier):
    '''
    Emails users when notify is called.
    '''
    # data_list is used for emails
    SCOPES = 'https://www.googleapis.com/auth/gmail.send'
    CLIENT_SECRET_FILE = 'client-secret.json'
    APPLICATION_NAME = 'IntruderBot'

    def __init__(self, email_list_file_path, is_enabled_setting_file_path):
        # set notifier setting name
        setting_for_is_enabled = "EmailNotifierOn"
        # initialise notifier
        super().__init__(email_list_file_path, setting_for_is_enabled, is_enabled_setting_file_path)

    def __get_receiver_email(self):
        '''
        Return list of reciever emails
        '''
        return self.get_data_list()
    
    def __set_message_reciever_details(self, message, receiver_email):
        '''
        Return message with reciever email set
        '''
        message["To"] = receiver_email
        return message
        
        
    def __set_email_content(self, intruder_info:IntruderInfo):
        """
        Helper function to set email content
        """
        subject = "Intruder Detected"
        bot_email = "botintruder@gmail.com"
        
        human_readable_time = intruder_info.detection_time.strftime('%d %B, %Y (%A) at %I:%M:%S %p %Z')
        message_body = f'Intruder detected at {human_readable_time} with certainty:{round(intruder_info.certainty_of_intruder, 2)}'

        # Create a multipart message and set headers
        message = MIMEMultipart()
        message["From"] = bot_email
        message["Subject"] = subject

        # Add body to email
        message.attach(MIMEText(message_body, "plain"))

        filename = intruder_info.image_path
        # Add file to email, as an ascii octet-stream (attachement)
        with open(filename, "rb") as attachment:
            part = MIMEImage(attachment.read(), _subtype="octet-stream")    
        encoders.encode_base64(part)

        # Header for attachement
        part.add_header(
            "Content-Disposition",
            'attachment', filename=filename)

        # Add attachment to message
        message.attach(part)
        return message
    
    def __message_to_string(self, message):
        # convert message to string
        return {'raw': base64.urlsafe_b64encode(message.as_string().encode()).decode()}


    def __send_message_internal(self, service, user_id, message):
        """
        Helper function to actually send the message
        """
        try:
            service.users().messages().send(userId=user_id, body=message).execute()
        except errors.HttpError as error:
            # incase there is an error, tell the user. Make the program sleep for 50 seconds while user fixes issue
            # We have to wait for a bit so that if there is an intruder, this popup doesn't keep showing up every single second there is motion if the notifer isn't working
            tkinter.messagebox.showerror(title="Error sending message", message=f"An error occurred: {error}")
            print('An error occurred: %s' % error)
            sleep(50)
    
    def __set_email_and_send_message(self, intruder_info: IntruderInfo, service, receiver_email):
        """
        Helper method to set email contentents and send the message
        """
        if not receiver_email:
            return
        message_to_send = self.__set_email_content(intruder_info)
        self.__set_message_reciever_details(message_to_send, receiver_email)
        msg_str = self.__message_to_string(message_to_send)
        self.__send_message_internal(service, "me", msg_str)

    def __get_credentials(self):
        '''
        Helper method to get credentials for sending out an email
        '''
        # get the credentials
        credential_dir = os.path.join(os.getcwd(), '.credentials')
        if not os.path.exists(credential_dir):
            os.makedirs(credential_dir)
        credential_path = os.path.join(credential_dir, 'intruder-bot-email.json')
        store = file.Storage(credential_path)
        credentials = store.get()
        if not credentials or credentials.invalid:
            # if credentials don't exist or have expired (invalid)
            # get new credentials and save them to a new file
            flow = client.flow_from_clientsecrets(self.CLIENT_SECRET_FILE, self.SCOPES)
            flow.user_agent = self.APPLICATION_NAME
            # promt user to enter email credentials 
            credentials = tools.run_flow(flow, store)
        return credentials
    
    def notify(self, intruder_info:IntruderInfo):
        '''
        Notify user by sending an email with intruder information
        '''
        if not self.get_enabled():
            return

        # get credentials
        credentials = self.__get_credentials()
    
        # authorise them
        http = credentials.authorize(httplib2.Http())
        service = discovery.build('gmail', 'v1', http=http)

        # set email content and send message for each reciever email
        threads = []
        for receiver_email in self.__get_receiver_email():
            print(receiver_email)
            # doing this in parallel for each user to save on time
            thread = Thread(target=self.__set_email_and_send_message, args=(intruder_info, service, receiver_email,))
            thread.start()
            threads.append(thread)

        # wait for all emails to be sent before moving on
        # so just incase there is an error in email sending, we will know immediately, before doing other things
        for thread in threads:
            thread.join()
        
        # timing util
        # email_time = time.perf_counter()
        # print(f"email finished at: {email_time} seconds")
