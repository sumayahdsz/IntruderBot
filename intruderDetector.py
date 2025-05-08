import math
from keras.preprocessing.image import ImageDataGenerator
from keras.models import Sequential, load_model
from keras.callbacks import EarlyStopping, ModelCheckpoint
from keras.layers import Convolution2D
from keras.layers import MaxPool2D
from keras.layers import Flatten
from keras.layers import Dense
import numpy as np
from keras.preprocessing import image
from collections import Counter
from os import listdir, path

from fileStorageUnit import FileStorageUnit

class IntruderDetector(FileStorageUnit):
    def __init__(self, training_image_path, data_list_file_path, image_dim_width=128, image_dim_length=128, notifiers_list=[]):
        """
        IntruderDetector contains a model to detect whether there is an intruder.
        the 0th element in __is_intruder_threshold_list contains the threshold for the IntruderDetector.
        If the prediction probabily of the person being safe is above this value, the program will think it is not an intruder.
        If the prediction probability is lower than this value, the program will think it is an intruder.
        """
        super().__init__(data_list_file_path)
        # __is_intruder_threshold_list is a pointer to the same list returned by get_data_list
        self.__is_intruder_threshold_list = self.get_data_list() 

        # training_image_path is the path where all the images are that are used for model training.
        # users can add image to this path through configure>add users
        self.__training_image_path = training_image_path

        # we set the image length and width so that testing and training data are the same size
        self.__image_dim_width = image_dim_width
        self.__image_dim_len = image_dim_length

        # notifiers list is a list of notifiers that get notified when there is an intruder.
        # the notifier will only notify if it is enabled.
        self.__notifiers_list = notifiers_list
        self.train_model()
    
    def train_model(self):
        """
        Trains the model based on provided data
        returns None
        """
        # Total number of data points  
        number_of_data_points = 0

        # assumes only image folders are in the training image path
        for directory in listdir(self.__training_image_path):
            num_files = len(listdir(path.join(self.__training_image_path,directory)))
            number_of_data_points+=num_files

        # images are grouped in batches for classification
        # https://datascience.stackexchange.com/questions/20179/what-is-the-advantage-of-keeping-batch-size-a-power-of-2
        # I have tweaked batch size to always be the min of 16, or a power of 2
        batch_size = min(16, 2**(math.floor(math.log2(number_of_data_points))))


        # Rescale 1/255 is to transform all pixel values from [0,255] to [0,1]
        train_datagen = ImageDataGenerator(rescale=1/255,
            validation_split=0.2)

        # Create training data
        train_generator = train_datagen.flow_from_directory(
            self.__training_image_path,
            batch_size=batch_size,
            target_size=(self.__image_dim_width, self.__image_dim_len),
            class_mode='categorical',
            subset='training')
        
        # Keeping track of number of classes and number of images
        counter = Counter(train_generator.classes) 
        num_samples = len(train_generator.classes)
        print(f'num_samples: {num_samples}')
        self.num_classes = len(counter.values())
        if self.num_classes == 0:
            # if there are no folders, don't train the model
            return
        print(f'num_classes: {self.num_classes}')
        
        # set class wieghts according to -> n_samples / (n_classes * np.bincount(y)
        class_weights = {class_id:  num_samples/(num_images*self.num_classes) for class_id, num_images in counter.items()}
      
        # Create validation data
        validation_generator = train_datagen.flow_from_directory(
            self.__training_image_path,
            batch_size=batch_size,
            target_size=(self.__image_dim_width, self.__image_dim_len),
            class_mode='categorical',
            subset='validation')

        test_set_person_to_node = validation_generator.class_indices
        self.node_to_person = dict((v,k) for k,v in test_set_person_to_node.items())
        num_output_nodes = len(self.node_to_person)

        '''######################## Create CNN deep learning model ########################'''

        '''Initializing the Convolutional Neural Network'''
        self.__model= Sequential()

        ''' STEP--1 Convolution
        # Adding the first layer of CNN
        # we are using the format (self.image_dim_width, self.image_dim_len,3) because we are using TensorFlow backend
        # It means 3 matrix of size (self.image_dim_width, self.image_dim_len) pixels representing Red, Green and Blue components of pixels
        '''
        self.__model.add(Convolution2D(32, kernel_size=(2, 2), strides=(1, 1), input_shape=(self.__image_dim_width, self.__image_dim_len,3), activation='softmax'))

        '''# STEP--2 MAX Pooling'''
        self.__model.add(MaxPool2D(pool_size=(2,2)))

        '''############## ADDITIONAL LAYER of CONVOLUTION for better accuracy #################'''
        self.__model.add(Convolution2D(self.__image_dim_width, kernel_size=(2, 2), strides=(1, 1), activation='softmax'))

        self.__model.add(MaxPool2D(pool_size=(2,2)))

        '''# STEP--3 FLattening'''
        self.__model.add(Flatten())

        '''# STEP--4 Fully Connected Neural Network'''

        self.__model.add(Dense(num_output_nodes, activation='softmax'))

        '''# Compiling the CNN'''
        self.__model.compile(loss='categorical_crossentropy', optimizer = 'adam', metrics=["accuracy"])

        early_stopping_callback = EarlyStopping(monitor='val_loss', mode='min', verbose=1, patience=50)
        best_model_callback = ModelCheckpoint('best_model.h5', monitor='val_accuracy', mode='max', verbose=1, save_best_only=True)


        # Starting the model training
        self.__model.fit(
            train_generator,
            steps_per_epoch = train_generator.samples // batch_size,
            validation_data = validation_generator, 
            validation_steps = validation_generator.samples // batch_size,
            epochs = 3000,
            callbacks=[early_stopping_callback, best_model_callback],
            class_weight=class_weights
        )
        
        # load the saved model
        self.__model = load_model('best_model.h5')
        
    def classify(self, image_path=None, test_image=""):
        """
        Classifies an image as intruder or not, **without** accounting for intruder threshold.

        User must specify either one of image_path or test_image. These variables relate to the image that needs classification:
        - image_path is the directory location / path of the image
        - test_image is the actual image object.
        Either ONE of these two fields need to be provided. Two ways of providing what image to classify are provided just for convenience.

        This function returns the model's prediction and confidence of the model's prediction.
        """
        # returns prediction and probabilty of prediction being correct
        if self.num_classes==0:
            # don't classify anything if there is no data
            return "no_classes", 1
        
        # If user provided image_path, use that. Else use test_image.
        if image_path:
            test_image=image.load_img(image_path,target_size=(self.__image_dim_len, self.__image_dim_width))
        test_image=image.img_to_array(test_image)
        test_image=np.expand_dims(test_image,axis=0)

        # if we have a model (model is done with training and number of classes > 0), classify the image
        if self.__model:
            result=self.__model.predict(test_image,verbose=0)
            prediction = self.node_to_person[np.argmax(result[0])]
            probabilty = float(max(result[0]))
            print('Prediction is: ', prediction , probabilty)
            return prediction, probabilty
        
        # this case may be hit if the model detects an intruder while it was re-training (e.g. when new images are uploaded)
        return "model_loading", 1
    
    def is_intruder(self, prediction, probabilty):
        """
        Classifies if the person is an intruder, consider both model prediction and intruder detection.
        Returns boolean indicating if person was an intruder or not, accounting for intruder threshold

        Definition of intruder threshold:
        # if prediciton was above the threshold and the prediction was a safe person, return not an intruder
        # if prediciton was above the threshold and the prediction was an intruder, return intruder. Else return intruder
        """
        is_safe_sure = ("__safe" in prediction) and float(probabilty) >= float(self.__is_intruder_threshold_list[0])
        # if prediciton was above the threshold and the prediction was a safe person, return not an intruder
        # if prediciton was above the threshold and the prediction was an intruder, return intruder. Else return intruder
        return not is_safe_sure
    
    def trigger_notifiers(self, intruder_info):
        """
        Trigger notifiers that belong to the model
        """
        for notifier in self.__notifiers_list:
            notifier.notify(intruder_info)

    def get_notifier(self):
        """
        Returns a list of notifiers linked to this model.
        Not currently used, but kept for potential future usage and manual testing.
        """
        return self.__notifiers_list 
    
    def set_is_intruder_threshold(self, is_intruder_threshold):
        """
        Returns None.
        Sets the list of notifiers linked to this model.
        """
        self.__is_intruder_threshold_list[0] = is_intruder_threshold
        self.set_data_list(self.__is_intruder_threshold_list)
    
    def get_is_intruder_threshold(self):
        """
        Returns the intruder threshold.
        Definition of intruder threshold:
        # if prediciton was above the threshold and the prediction was a safe person, return not an intruder
        # if prediciton was above the threshold and the prediction was an intruder, return intruder. Else return intruder
        """
        return self.__is_intruder_threshold_list[0]

    

        
