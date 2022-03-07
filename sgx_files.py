import os, glob, shutil
import numpy as np
from pyunpack import Archive
import pickle
from time import time, sleep
from sgx_image import assemble_images
from datetime import date, datetime
import cv2

class SGX_folder:
    def __init__(self, watch_folder_path, dest_image_folder, scan_rate):
        self.project_root = os.path.dirname(os.path.abspath(__file__))
        self.watch_folder_path = watch_folder_path
        self.dest_image_folder = dest_image_folder
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
        self.current_file_list = glob.glob("*.tif")
        return self.current_file_list

    def check_for_new_files(self, old_file_list):
        self.new_files = np.setdiff1d(self.current_file_list, old_file_list)
        return self.new_files

    def download_tif_file(self, filename, attempts=0):
        # download the new one
        os.chdir(self.project_root)
        source_path = self.watch_folder_path + "\\" + filename
        max_attempts = 100
        if attempts == 0:
            print('downloading file {}...'.format(filename))
        try:
            image = cv2.imread(source_path)
            print('downloaded file {} after {} attempts'.format(filename, attempts + 1))
        except:
            if attempts < max_attempts:
                self.sleep()
                attempts += 1
                self.download_tif_file(filename, attempts)
            else:
                print('failed to load file after {} attempts'.format(attempts))
                return None
        return image

    def merge_images(self, image1, image2, sgx_identifiers):
        if image1.identifier == sgx_identifiers.bf_id:
            bf_filename = image1.filename
            df_filename = image2.filename
        else:
            bf_filename = image2.filename
            df_filename = image1.filename
        from sgx_image import show_image
        bf_image = self.download_tif_file(bf_filename)
        df_image = self.download_tif_file(df_filename)
        merged_image = combine_channels(bf_image, df_image)
        file_id_len = len(bf_filename) - len(sgx_identifiers.bf_id) - 4
        file_id = bf_filename[0:file_id_len]
        cmb_file_name = file_id + '_' + sgx_identifiers.cf_id + '.tif'
        cmb_path = self.dest_image_folder + '\\' + cmb_file_name
        print('saving {}'.format(cmb_file_name))
        cv2.imwrite(cmb_path, merged_image)

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


class SGX_identifiers:
    def __init__(self, bf_id, df_id, cf_id):
        self.bf_id = bf_id
        self.df_id = df_id
        self.cf_id = cf_id

class SGX_file:
    def __init__(self, filename, identifier_length, file_extension_length):
        self.filename = filename
        self.recipe = ""
        self.year = 0
        self.month = 0
        self.day = 0
        self.hour = 0
        self.minute = 0
        self.second = 0
        self.identifier = ""
        self.parse_filename(identifier_length, file_extension_length)

    def parse_filename(self, identifier_length, file_extension_length):
        self.year, year_index = self.find_year()
        self.recipe = self.filename[0:year_index-1]
        month_index = year_index + 5
        self.month = int(self.filename[month_index:month_index+2])
        day_index = month_index + 3
        self.day = int(self.filename[day_index:day_index+2])
        hour_index = day_index + 3
        self.hour = int(self.filename[hour_index:hour_index+2])
        minute_index = hour_index + 3
        self.minute = int(self.filename[minute_index:minute_index+2])
        second_index = minute_index + 3
        self.second = int(self.filename[second_index:second_index+2])
        identifier_index = second_index + 3
        if identifier_index > len(self.filename) - (file_extension_length+1):
            self.indentifier = ""
        else:
            self.identifier = self.filename[identifier_index:identifier_index+identifier_length]

    def find_year(self):
        current_year = date.today().year
        year_index = self.filename.find(str(current_year))
        if year_index == -1:
            current_year -= 1
            year_index = self.filename.find(str(current_year))
        return current_year, year_index


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

def found_matching_files(file_one, file_two):

    if file_one.identifier == file_two.identifier:
        return False
    elif file_one.recipe != file_two.recipe:
        return False
    datetime1 = datetime(file_one.year, file_one.month, file_one.day, file_one.hour, file_one.minute, file_one.second, 0)
    datetime2 = datetime(file_two.year, file_two.month, file_two.day, file_two.hour, file_two.minute, file_two.second, 0)
    diff_timedelta = abs(datetime2 - datetime1)
    diff = int(diff_timedelta.total_seconds())
    if diff > 5:
        return False
    else:
        return True

def combine_channels(bf_cropped_image, df_cropped_image):
    # create combined image
    bf_channel = bf_cropped_image[:, :, 0]
    df_channel = np.subtract(255, df_cropped_image[:, :, 0])
    y_slice = 10
    width = min(len(bf_channel[0]), len(df_channel[0]))
    height = min(len(bf_channel), len(df_channel))
    bf_channel = bf_channel[y_slice:height, 0:width]
    df_channel = df_channel[0:height-y_slice, 0:width]
    combined_channel = np.divide(np.add(bf_channel, df_channel), 2).astype('uint8')
    combined_channel_normalized = np.zeros((len(combined_channel), len(combined_channel[0])))
    combined_channel_normalized = cv2.normalize(combined_channel, combined_channel_normalized, 0, 255, cv2.NORM_MINMAX).astype('uint8')
    # combined_channel_normalized = combined_channel
    combined_image = np.zeros((len(bf_channel), len(bf_channel[0]), 3)).astype('uint8')
    combined_image[:, :, 2] = bf_channel
    combined_image[:, :, 1] = df_channel
    combined_image[:, :, 0] = combined_channel_normalized
    return combined_image