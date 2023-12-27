    
class FileStorageUnit:
    """
    File storage unit assists with the reading and writing to the file
    at file path data_list_file_path
    """
    def __init__(self, data_list_file_path:str):
        """
        Initialise file storage unit, storing info at the provided path
        """
        # I use the data_list variable so that there is less i/o to keep
        # reading from the file for information.
        self.__data_list = []
        self.__data_list_file_path = data_list_file_path
        self.__load_data_from_file()

    def __load_data_from_file(self):
        """
        Load data from file path into __data_list
        """
        with open(self.__data_list_file_path, "r") as filestream:
            for line in filestream:
                self.__data_list.append(line.strip())

    def __save_data_list_to_file(self):
        """
        Store data from __data_list to file path
        """
        with open(self.__data_list_file_path, "w") as filestream:
            for line in self.__data_list:
               # save element from list to file
               filestream.write(line.strip()+"\n")
    
    def get_data_list(self):
        """
        Accessor method that returns a list of data in the file
        where each line in the file is a string in the list
        """
        return self.__data_list
    
    def set_data_list(self, data_list):
        """
        Sets value in the list and saves it to file
        """
        self.__data_list = data_list
        self.__save_data_list_to_file()