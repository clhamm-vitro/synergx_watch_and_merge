import os, glob, shutil
from os.path import exists as file_exists
import numpy as np
from pyunpack import Archive
import pickle
from time import time, sleep
from datetime import date, datetime, timedelta
import cv2

class SGX_folder:
    def __init__(self, watch_folder_path, dest_image_folder, scan_rate):
        self.project_root = os.path.dirname(os.path.abspath(__file__))
        self.watch_folder_path = watch_folder_path
        self.dest_image_folder = dest_image_folder
        self.scan_rate = scan_rate
        self.current_file_list = []
        self.new_files = []
        self.persistent_data_path = os.path.dirname(os.path.abspath(__file__)) + '/' + 'persistent_data.pkl'
        self.persistent_data = self.initialize_persistent_data()
        self.max_sequential_number = 9999


    def get_file_list(self):
        try:
            os.chdir(self.watch_folder_path)
        except:
            cmd = "net use {} /PERSISTENT:YES /USER:{} {}".format(self.watch_folder_path, '.\\vitro', 'vitro')
            os.system(cmd)
            self.get_file_list()
        self.current_file_list = glob.glob("*.tif")
        return self.current_file_list

    def find_a_match(self, sgx_file):
        other_sgx_file = sgx_file.get_other_sgx_file()
        attempts = 50
        file_name_straddle = 2
        os.chdir(self.project_root)
        for attempts in range(attempts):
            for s in range(-file_name_straddle, file_name_straddle+1):
                current_search_file = other_sgx_file.edit_and_clone(s)
                source_path = self.watch_folder_path + "\\" + current_search_file.filename
                if file_exists(source_path):
                    return current_search_file
        print("no match found")
        return None

    def check_for_new_files(self, old_file_list):
        self.new_files = np.setdiff1d(self.current_file_list, old_file_list)
        return self.new_files

    def download_tif_file(self, filename, attempts=0, max_attempts=100, printing=True):
        # download the new one
        os.chdir(self.project_root)
        source_path = self.watch_folder_path + "\\" + filename
        if not file_exists(source_path):
            return None
        if attempts == 0:
            if printing:
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
                if printing:
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
        bf_image, df_image, cf_image = combine_channels(bf_image, df_image)
        # file_id_len = len(bf_filename) - len(sgx_identifiers.bf_id) - 4
        # file_id = bf_filename[0:file_id_len]

        return bf_image, df_image, cf_image

    def save_and_rename(self, first_file, bf_image, df_image, cf_image, spyglass_identifiers):
        sequential_number = self.persistent_data['sequential_number']
        file_id = first_file.build_file_id(sequential_number)
        bf_file_name = file_id + "_" + spyglass_identifiers.bf_id + ".tif"
        df_file_name = file_id + "_" + spyglass_identifiers.df_id + ".tif"
        cf_file_name = file_id + "_" + spyglass_identifiers.cf_id + ".tif"
        bf_path = self.dest_image_folder + '\\' + bf_file_name
        df_path = self.dest_image_folder + '\\' + df_file_name
        cf_path = self.dest_image_folder + '\\' + cf_file_name
        print('saving {}'.format(bf_file_name))
        cv2.imwrite(bf_path, bf_image)
        print('saving {}'.format(df_file_name))
        cv2.imwrite(df_path, df_image)
        print('saving {}'.format(cf_file_name))
        cv2.imwrite(cf_path, cf_image)
        self.update_persistent_data()


    def update_persistent_data(self):
        sequential_number = self.persistent_data['sequential_number']
        if sequential_number < self.max_sequential_number:
            self.persistent_data['sequential_number'] += 1
        else:
            self.persistent_data['sequential_number'] = 0
        save_persistent_data(self.persistent_data, self.persistent_data_path)


    def initialize_persistent_data(self):
        if os.path.isfile(self.persistent_data_path):
            return load_persistant_data(self.persistent_data_path)
        else:
            persistent_data = {'sequential_number': 0}
            return persistent_data

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


def save_persistent_data(data, pickel_path):
    with open(pickel_path, 'wb') as f:
        pickle.dump(data, f)


class Image_identifiers:
    def __init__(self, bf_id, df_id, cf_id):
        self.bf_id = bf_id
        self.df_id = df_id
        self.cf_id = cf_id

class SGX_file:
    def __init__(self, filename, identifier_length, file_extension_length, identifiers):
        self.filename = filename
        self.file_extension_length = file_extension_length
        self.identifier_length = identifier_length
        self.identifiers = identifiers
        self.recipe = ""
        self.year = 0
        self.month = 0
        self.day = 0
        self.hour = 0
        self.minute = 0
        self.second = 0
        self.identifier = ""
        self.parse_filename()
        self.datetime = datetime(year=self.year, month=self.month, day=self.day,
                                 hour=self.hour, minute=self.minute, second=self.second, microsecond=0)

    def get_other_sgx_file(self):
        base_filename_len = len(self.filename) - (self.file_extension_length+1) - len(self.identifier) - 1
        base_filename = self.filename[0:base_filename_len]
        if self.identifier == self.identifiers.df_id:
            new_identifier = self.identifiers.bf_id
        else:
            new_identifier = self.identifiers.df_id
        if len(new_identifier) > 0:
            new_filename = base_filename + "_" + new_identifier + ".tif"
        else:
            new_filename = base_filename + ".tif"
        return SGX_file(new_filename, self.identifier_length, self.file_extension_length, self.identifiers)

    def build_file_id(self, sequential_num):
        sequential_number = '{:04d}'.format(sequential_num)
        date_string, time_string = self.get_date_and_time_string()
        file_id = sequential_number + '_' + date_string + '_' + time_string
        return file_id

    def get_date_and_time_string(self):
        date_string = '{:04d}{:02d}{:02d}'.format(self.year, self.month, self.day)
        time_string = '{:0d}{:02d}{:02d}'.format(self.hour, self.minute, self.second)
        return date_string, time_string

    def parse_filename(self):
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
        if identifier_index > len(self.filename) - (self.file_extension_length+1):
            self.indentifier = ""
        else:
            self.identifier = self.filename[identifier_index:identifier_index+self.identifier_length]

    def find_year(self):
        current_year = date.today().year
        year_index = self.filename.find(str(current_year))
        if year_index == -1:
            current_year -= 1
            year_index = self.filename.find(str(current_year))
        return current_year, year_index

    def edit_and_clone(self, seconds_offset):
        new_datetime = self.datetime + timedelta(seconds=seconds_offset)
        date_string = '{:04d}_{:02d}_{:02d}'.format(new_datetime.year, new_datetime.month, new_datetime.day)
        time_string = '{:0d}_{:02d}_{:02d}'.format(new_datetime.hour, new_datetime.minute, new_datetime.second)
        new_filename = "{}_{}_{}".format(self.recipe, date_string, time_string)
        if len(self.identifier) > 0:
            new_filename += "_" + self.identifier + ".tif"
        else:
            new_filename += ".tif"
        return SGX_file(new_filename, self.identifier_length, self.file_extension_length, self.identifiers)

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
    df_channel = df_cropped_image[:, :, 0]
    y_slice = 10
    width = min(len(bf_channel[0]), len(df_channel[0]))
    height = min(len(bf_channel), len(df_channel))
    bf_channel = bf_channel[y_slice:height, 0:width]
    df_channel = df_channel[0:height-y_slice, 0:width]
    df_channel_negative = np.subtract(255, df_channel)

    combined_channel = np.divide(np.add(bf_channel, df_channel_negative), 2).astype('uint8')
    combined_channel_normalized = np.zeros((len(combined_channel), len(combined_channel[0])))
    combined_channel_normalized = cv2.normalize(combined_channel, combined_channel_normalized, 0, 255, cv2.NORM_MINMAX).astype('uint8')
    # combined_channel_normalized = combined_channel
    combined_image = np.zeros((len(bf_channel), len(bf_channel[0]), 3)).astype('uint8')
    combined_image[:, :, 2] = bf_channel
    combined_image[:, :, 1] = df_channel_negative
    combined_image[:, :, 0] = combined_channel_normalized
    return bf_channel, df_channel, combined_image

def  load_persistant_data(pickel_path):
    with open(pickel_path, 'rb') as f:
        previous_gi_files = pickle.load(f)
    return previous_gi_files