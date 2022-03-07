import os, glob, shutil
import numpy as np
from pyunpack import Archive
import pickle
from time import time, sleep
from sgx_image import assemble_images

class SGX_folder:
    def __init__(self, watch_folder_path, dest_image_folder, gi_store_path, gi_unzip_path, scan_rate):
        self.project_root = os.path.dirname(os.path.abspath(__file__))
        self.watch_folder_path = watch_folder_path
        self.dest_image_folder = dest_image_folder
        self.gi_store_path = gi_store_path
        self.gi_unzip_path = gi_unzip_path
        self.image_folder_path = os.path.dirname(os.path.abspath(__file__)) + '/' + 'images'
        self.scan_rate = scan_rate
        self.current_file_list = []
        self.new_files = []




    def get_file_list(self):
        try:
            os.chdir(self.watch_folder_path)
        except:
            cmd = "net use {} /PERSISTENT:YES /USER:{} {}".format(self.watch_folder_path, '.\\vitro', 'vitro')
            os.system(cmd)
            self.get_file_list()
        self.current_file_list = glob.glob("*.GI")
        return self.current_file_list


    def check_for_new_files(self, old_file_list):
        self.new_files = np.setdiff1d(self.current_file_list, old_file_list)
        return self.new_files

    def download_gi_files(self, num_files=None):
        # delete the old gi files in the local gi folder

        self.clear_directory(self.gi_store_path)

         # download the new ones
        os.chdir(self.project_root)
        new_files = len(self.new_files)
        if num_files is None:
            for f in self.new_files:
                print('downloading {} more files from SGX watch folder...'.format(new_files))
                file_path = self.watch_folder_path + "/" + f
                shutil.copy(file_path, self.gi_store_path)
                new_files -= 1
        else:
            start = len(self.new_files) - (num_files + 1)
            end = len(self.new_files) - 1
            self.new_files = self.new_files[start:end]
            for i in range(num_files):
                print('downloading {} more files from SGX watch folder...'.format(num_files-i))

                index = i
                file_path = self.watch_folder_path + "/" + self.new_files[index]
                shutil.copy(file_path, self.gi_store_path)
                new_files -= 1

    def download_gi_file(self, filename, attempts=0):
        # delete the old gi files in the local gi folder
        self.clear_directory(self.gi_store_path)
        # download the new one
        os.chdir(self.project_root)
        source_path = self.watch_folder_path + "\\" + filename
        dest_path = self.gi_store_path + "\\" + filename
        max_attempts = 100
        if attempts == 0:
            print('downloading file {}...'.format(filename))
        try:
            shutil.copy(source_path, dest_path)
            print('downloaded file {} after {} attempts'.format(filename, attempts + 1))
        except:
            if attempts < max_attempts:
                self.sleep()
                attempts += 1
                self.download_gi_file(filename, attempts)
            else:
                print('failed to load file after {} attempts'.format(attempts))


    def unzip_gi_files(self):
        # delete the old unzipped files in the local gi folder
        self.clear_directory(self.gi_unzip_path)
        new_files = len(self.new_files)
        for f in self.new_files:
            print('extracting GI file...')
            # print('extracting {} more GI files...'.format(new_files))
            source_path = self.gi_store_path + "/" + f
            filename = f[:-3]
            destination_path = self.gi_unzip_path + "/" + filename
            os.mkdir(destination_path)
            extract(source=source_path, destination=destination_path)
            new_files -= 1

    def clear_directory(self, dir):
        os.chdir(self.project_root)
        for f in os.listdir(dir):
            file_path = os.path.join(dir, f)
            if os.path.isfile(file_path):
                os.remove(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)

    def sleep(self):
        sleep((self.scan_rate / 1000) - time() % (self.scan_rate / 1000))

    def process_file(self, filename):
        # download and unzip the GI file
        self.download_gi_file(filename)
        self.unzip_gi_files()

        # assemble BF & DF halves
        self.clear_directory(self.image_folder_path)
        image_BF, image_DF, image_combined = assemble_images(gi_unzip_path=self.gi_unzip_path,
                                                             dest_image_folder=self.dest_image_folder)

        # save BF and DF separately to outputfolder_separate

        # create combined BF, DF, & difference image

        # save combined image to outputfolder_combined

def extract(source, destination):
    Archive(source).extractall(destination)

def  load_old_gi_file_list():
    previous_gi_file_list_name = 'previous_gi_file_list.pkl'
    pickel_path = os.path.dirname(os.path.abspath(__file__)) + '/' + previous_gi_file_list_name
    with open(pickel_path, 'rb') as f:
        previous_gi_files = pickle.load(f)
    return previous_gi_files



def save_gi_file_list(current_file_list):
    previous_gi_file_list_name = 'previous_gi_file_list.pkl'
    pickel_path = os.path.dirname(os.path.abspath(__file__)) + '/' + previous_gi_file_list_name
    with open(pickel_path, 'wb') as f:
        pickle.dump(current_file_list, f)
    print('saved list of files!')

