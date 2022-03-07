import os
import glob
import re
from copy import deepcopy
import sys
from datetime import datetime
import pickle
from PIL import Image
import cv2
import numpy as np
import time

class SGX_image:
    def __init__(self, name, dest_image_folder, bright, dark, horizontal_stitching=False, combined_image=True,
                 combined_image_dest_folder='\\\\10.53.9.115\\sgx_cmb'):
        self.name = name
        self.horizontal_stitching = horizontal_stitching
        self.bright = bright
        self.dark = dark
        self.project_root = os.path.dirname(os.path.abspath(__file__))
        # self.source = self.project_root + '/gi_unzip/' + name
        self.source = self.project_root + '\\gi_unzip\\' + name
        # self.destination_root = self.project_root + '/images'
        self.destination_root = self.project_root + '\\images'
        # self.destination = self.destination_root + '/' + name
        self.destination = self.destination_root + '\\' + name
        self.image_patches = self.get_image_patches()
        self.black_thresh = 25
        # self.white_thresh = 230
        # self.white_thresh = 220
        self.white_thresh = 180
        self.dest_image_folder = dest_image_folder
        self.combined_image = combined_image
        if combined_image_dest_folder is not None:
            self.combined_image_dest_folder = combined_image_dest_folder
        else:
            self.combined_image_dest_folder = dest_image_folder
        self.persistent_data_path = os.path.dirname(os.path.abspath(__file__)) + '/' + 'persisent_data.pkl'
        self.persistent_data = self.initialize_persistent_data()
        self.max_sequential_number = 9999
        if self.bright:
            self.bright_field_patches = self.get_field_patches('bright')
        if self.dark:
            self.dark_field_patches = self.get_field_patches('dark')

    def initialize_persistent_data(self):
        if os.path.isfile(self.persistent_data_path):
            return load_persistant_data(self.persistent_data_path)
        else:
            persistent_data = {'sequential_number': 0}
            return persistent_data

    def build_and_save(self):
        top_padding = 1200
        bottom_padding = 500
        left_padding = 500

        # match halves
        bf_raw_image, bf_top_raw = self.assemble_image('bright', self.bright_field_patches)
        bf_bottom_raw = self.calculate_bottom(bf_raw_image, 'bright')
        # y_search = int(round((bf_top_raw+bf_bottom_raw)/2))
        y_search = int(3 * round((bf_top_raw+bf_bottom_raw)/4))
        bf_left_raw = self.calculate_left(bf_raw_image, 'bright', y_search)
        bf_right_raw = self.calculate_right(bf_raw_image, 'bright', y_search)

        bf_top = max(0, bf_top_raw-top_padding)
        bf_bottom = min(len(bf_raw_image), bf_bottom_raw+bottom_padding)
        bf_left = max(bf_left_raw-left_padding, 0)
        bf_right = min(len(bf_raw_image[0]), bf_right_raw+left_padding)

        df_raw_image, df_top_raw = self.assemble_image('dark', self.dark_field_patches)
        df_bottom_raw = self.calculate_bottom(df_raw_image, 'dark')
        # y_search = int(round((df_top_raw + df_bottom_raw) / 2))
        y_search = int(3 * round((df_top_raw + df_bottom_raw) / 4))
        df_left_raw = self.calculate_left(df_raw_image, 'dark', y_search)
        df_right_offset = 4
        df_top_offset = -4
        df_top_raw += df_top_offset
        df_right_raw = self.calculate_right(df_raw_image, 'dark', y_search) + df_right_offset


        y_scale_factor = (bf_bottom_raw-bf_top_raw)/(df_bottom_raw-df_top_raw)
        x_scale_factor = (bf_right_raw-bf_left_raw)/(df_right_raw-df_left_raw)
        df_top = max(0, df_top_raw - int(round(top_padding/y_scale_factor)))
        df_bottom = min(len(df_raw_image), df_bottom_raw + int(round(bottom_padding/y_scale_factor)))
        df_left = max(df_left_raw - int(round(left_padding/x_scale_factor)), 0)
        df_right = min(len(df_raw_image[0]), df_right_raw+int(round(left_padding/x_scale_factor)))

        bf_right = min(bf_right, int(round(df_right*x_scale_factor)))
        df_right = int(round(bf_right/x_scale_factor))
        bf_cropped_image = bf_raw_image[bf_top:bf_bottom, bf_left:bf_right]
        df_cropped_image = df_raw_image[df_top:df_bottom, df_left:df_right]

        # scale DF
        show_image('bf', bf_raw_image)
        show_image('df', df_raw_image)
        print('BF left: {}, right: {}, top: {}, bottom: {}'.format(bf_left, bf_right, bf_top, bf_bottom))
        print('DF left: {}, right: {}, top: {}, bottom: {}'.format(df_left, df_right, df_top, df_bottom))
        dim = (int(round(len(df_cropped_image[0]) * x_scale_factor)), int(round(len(df_cropped_image) * y_scale_factor)))
        df_cropped_image = cv2.resize(df_cropped_image, dim, interpolation=cv2.INTER_AREA)
        height = min(len(bf_cropped_image), len(df_cropped_image))
        width = min(len(bf_cropped_image[0]), len(df_cropped_image[0]))
        bf_cropped_image = bf_cropped_image[0:height, 0:width]
        bf_cropped_image = rotate_image(bf_cropped_image, 0.1)
        df_cropped_image = df_cropped_image[0:height, 0:width]
        # show_image('bf', bf_cropped_image)
        # show_image('df', df_cropped_image)

        if self.combined_image:
            combined_image = combine_channels(bf_cropped_image, df_cropped_image)
        else:
            combined_image = None

        # save the files
        self.save_files(bf_cropped_image, df_cropped_image, combined_image)
        # update persistent data
        self.update_persistent_data()

        return bf_cropped_image, df_cropped_image, combined_image





    def save_files(self, bf_image, df_image, combined_image):
        file_id = self.build_file_id()
        bf_file_name = file_id + '_BRT.tif'
        bf_path = self.dest_image_folder + '\\' + bf_file_name
        df_file_name = file_id + '_DRK.tif'
        df_path = self.dest_image_folder + '\\' + df_file_name
        print('saving {}'.format(bf_file_name))
        cv2.imwrite(bf_path, bf_image)
        print('saving {}'.format(df_file_name))
        start_time = time.time()
        cv2.imwrite(df_path, df_image)
        end_time = time.time()
        print('DF save lag: {:.2f} seconds'.format(end_time-start_time))
        if combined_image is not None:
            cmb_file_name = file_id + '_CMB.tif'
            cmb_path = self.combined_image_dest_folder + '\\' + cmb_file_name
            print('saving {}'.format(cmb_file_name))
            cv2.imwrite(cmb_path, combined_image)

    def build_file_id(self):
        sequential_number = '{:04d}'.format(self.persistent_data['sequential_number'])
        date_string, time_string = self.get_date_and_time_string()
        file_id = sequential_number + '_' + date_string + '_' + time_string
        return file_id

    def get_date_and_time_string(self):
        now = datetime.now()
        date_string = '{:04d}{:02d}{:02d}'.format(now.year, now.month, now.day)
        time_string = '{:0d}{:02d}{:02d}'.format(now.hour, now.minute, now.second)
        return date_string, time_string

    def update_persistent_data(self):
        sequential_number = self.persistent_data['sequential_number']
        if sequential_number < self.max_sequential_number:
            self.persistent_data['sequential_number'] += 1
        else:
            self.persistent_data['sequential_number'] = 0

        save_persistant_data(self.persistent_data, self.persistent_data_path)


    def get_image_patches(self):
        os.chdir(self.source)
        tiffs = glob.glob("**\\*.TIFF", recursive=True)
        image_patches = self.parse_tiffs(tiffs)
        return image_patches

    def get_field_patches(self, field_type):
        field_patches = []
        for ip in self.image_patches:
            if ip.is_bright_field and field_type == 'bright':
                field_patches.append(ip)
            elif not ip.is_bright_field and field_type == 'dark':
                field_patches.append(ip)
        field_patches.sort(key=lambda x: int(x.y_position), reverse=True)
        vertical_patch_lists = self.get_vertical_patch_lists(field_patches)
        return vertical_patch_lists

    def parse_tiffs(self, tiffs):
        image_patches = []
        for tiff in tiffs:
            parsed_tiff = re.split('_|\\\\|\.', tiff)
            parsed_tiff.append(tiff)
            image_patches.append(Image_patch(parsed_tiff))
        return image_patches

    def get_vertical_patch_lists(self, image_patches):
        patches = deepcopy(image_patches)
        left_vertical_patches = []
        right_vertical_patcheds = []
        current_patch = patches.pop()
        while len(patches) > 0:
            if current_patch.is_left:
                left_vertical_patches.append(current_patch)
            else:
                right_vertical_patcheds.append(current_patch)
            if len(patches) > 0:
                current_patch = patches.pop()
        return {'left': left_vertical_patches, 'right': right_vertical_patcheds}


    def assemble_image(self, field_type, patches):
        # combine vertically
        horizontal_patches = []
        left_image = self.combine_patches(patches=patches['left'], direction='vertical')
        right_image = self.combine_patches(patches=patches['right'], direction='vertical')
        np_left_image = np.array(left_image)
        np_right_image = np.array(right_image)
        if field_type == "bright":
            # x_offset = -72
            x_offset = -78
        else:
            x_offset = -10
        left_top = self.calculate_top(field_type, np_left_image, 'left', x_offset)
        right_top = self.calculate_top(field_type, np_right_image, 'right', x_offset)
        if left_top is None or right_top is None:
            y_offset = -168
            if field_type == 'dark':
                y_offset = int(round(y_offset / 2))
        else:
            y_offset = left_top - right_top
        # combine horizontal
        new_im = self.combine_horizontal(images=[left_image, right_image], x_offset=x_offset, y_offset=y_offset)
        new_im.save(self.destination + "_" + field_type + ".TIFF")
        return np.array(new_im), left_top

    def combine_horizontal(self, images, x_offset, y_offset):
        widths, heights = zip(*(i.size for i in images))
        new_image_width = sum(widths)
        new_image_height = max(heights)

        # y_offset = -168
        new_im = Image.new('RGB', (new_image_width+abs(x_offset), new_image_height+abs(y_offset)))

        offset = 0
        for i in range(len(images)):
            im = images[i]

            if i == 0:
                current_y_offset = 0
            else:
                current_y_offset += y_offset
                offset += x_offset
            new_im.paste(im, (offset, current_y_offset))
            offset += im.size[0]

        return new_im

    def combine_patches(self, patches=None, direction='horizontal', images=None):
        if images == None:
            images = [Image.open(x.full_name) for x in patches]
        widths, heights = zip(*(i.size for i in images))
        is_horizontal = direction == 'horizontal'
        if is_horizontal:
            new_image_width = sum(widths)
            new_image_height = max(heights)
            y_offset = -168
            #x_offset = -72
            x_offset = 0
        else:
            new_image_width = max(widths)
            new_image_height = sum(heights)
            y_offset = 0
            x_offset = 0
        new_im = Image.new('RGB', (new_image_width+abs(x_offset), new_image_height+abs(y_offset)))

        offset = 0
        for i in range(len(images)):
            im = images[i]
            if is_horizontal:
                if i == 0:
                    current_y_offset = 0
                else:
                    current_y_offset += y_offset
                    offset += x_offset
                new_im.paste(im, (offset, current_y_offset))
                offset += im.size[0]
            else:
                new_im.paste(im, (0, offset))
                offset += im.size[1]
        return new_im

    def __str__(self):
        return 'left: {}, {}, right: {}, {}'.format(self.left.y_position, self.left.is_left, self.right.y_position,
                                                    self.right.is_left)

    def calculate_top(self, field_type, image, left_right, x_offset):
        if left_right == 'left':
            width = len(image[0])
            x_search = int(round(width + x_offset / 2))
        else:
            x_search = int(round(-1 * x_offset / 2))
        for i in range(len(image)):
            intensity = image[i][x_search][0]
            if field_type == "bright" and intensity <= self.black_thresh:
                return i
            elif field_type == "dark" and intensity >= self.white_thresh:
                return i
        return None

    def calculate_bottom(self, image, field_type):
        y_start = len(image) - 1
        if field_type == 'bright':
            x_search = int(round(len(image[0])/2) - 300)
        else:
            x_search = int(round(len(image[0])/2) - 150)

        for i in range(2000):
            intensity = image[y_start-i][x_search][0]
            if field_type == "bright" and intensity != 0 and intensity <= self.black_thresh:
                return y_start - i
            elif field_type == "dark" and intensity >= self.white_thresh:
                return y_start - i
        return y_start - 2000

    def calculate_left(self, image, field_type, y_search):
        for i in range(len(image[0])):
            intensity = image[y_search][i][0]
            if field_type == "bright" and intensity <= self.black_thresh:
                return i
            elif field_type == "dark" and intensity >= self.white_thresh:
                return i
        return 0

    def calculate_right(self, image, field_type, y_search):
        x_start = len(image[0]) - 1
        for i in range(2000):
            intensity = image[y_search][x_start-i][0]
            if field_type == "bright" and intensity != 0 and intensity <= self.black_thresh:
                return x_start - i
            elif field_type == "dark" and intensity >= self.white_thresh:
                return x_start - i
        print('oops! I didn\'t find an edge :(')
        return x_start - 2000


class Image_patch:
    def __init__(self, parsed_tiff):
        self.full_name = parsed_tiff[11]
        self.id = parsed_tiff[4] + '_' + parsed_tiff[5] + '_' + parsed_tiff[6]
        self.is_bright_field = parsed_tiff[9] == '0'
        self.is_left = parsed_tiff[8] == '0'
        self.y_position = parsed_tiff[6]


    def __str__(self):
        return "id: {}, is_bright_field: {}, is_left: {}, y_position: {}".format(self.id, self.is_bright_field,
                                                                                 self.is_left, self.y_position)


def get_raw_images(dir):
    source = os.path.dirname(os.path.abspath(__file__)) + "/" + dir
    raw_images = os.listdir(source)
    return raw_images

def assemble_images(gi_unzip_path, dest_image_folder, horizontal_stitching=True, bright=True, dark=True):
    raw_image = get_raw_images(gi_unzip_path)[0]
    sgx_image = SGX_image(name=raw_image, dest_image_folder=dest_image_folder, bright=bright, dark=dark,
                          horizontal_stitching=horizontal_stitching)
    bf, df, cmb = sgx_image.build_and_save()
    return bf, df, cmb



def get_list_of_images(path):
    os.chdir(path)
    list_of_images = glob.glob("*.TIFF")
    for i in range(len(list_of_images)):
        list_of_images[i] = path + '/' + list_of_images[i]
    return list_of_images


def show_image(image_name, image):
    image_small = ResizeWithAspectRatio(image, height=1000)
    cv2.imshow(image_name, image_small)
    while True:
        k = cv2.waitKey(100)  # change the value from the original 0 (wait forever) to something appropriate
        if k == 27:
            print('ESC')
            cv2.destroyAllWindows()
            break
        if cv2.getWindowProperty(image_name, cv2.WND_PROP_VISIBLE) < 1:
            break
    cv2.destroyAllWindows()


def ResizeWithAspectRatio(image, width=None, height=None, inter=cv2.INTER_AREA):
    dim = None
    (h, w) = image.shape[:2]

    if width is None and height is None:
        return image
    if width is None:
        r = height / float(h)
        dim = (int(w * r), height)
    else:
        r = width / float(w)
        dim = (width, int(h * r))
    return cv2.resize(image, dim, interpolation=inter)

def  load_persistant_data(pickel_path):
    with open(pickel_path, 'rb') as f:
        previous_gi_files = pickle.load(f)
    return previous_gi_files

def save_persistant_data(data, pickel_path):
    with open(pickel_path, 'wb') as f:
        pickle.dump(data, f)

def combine_channels(bf_cropped_image, df_cropped_image):
    # create combined image
    bf_channel = bf_cropped_image[:, :, 0]
    df_channel = np.subtract(255, df_cropped_image[:, :, 0])

    combined_channel = np.divide(np.add(bf_channel, df_channel), 2).astype('uint8')
    combined_channel_normalized = np.zeros((len(combined_channel), len(combined_channel[0])))
    combined_channel_normalized = cv2.normalize(combined_channel, combined_channel_normalized, 0, 255, cv2.NORM_MINMAX).astype('uint8')
    # combined_channel_normalized = combined_channel
    combined_image = np.zeros((len(bf_channel), len(bf_channel[0]), 3)).astype('uint8')
    combined_image[:, :, 2] = bf_channel
    combined_image[:, :, 1] = df_channel
    combined_image[:, :, 0] = combined_channel_normalized
    combined_image = cv2.normalize(combined_image, combined_image, 0, 255, cv2.NORM_MINMAX)
    return combined_image

def rotate_image(image, angle):
  image_center = tuple(np.array(image.shape[1::-1]) / 2)
  rot_mat = cv2.getRotationMatrix2D(image_center, angle, 1.0)
  result = cv2.warpAffine(image, rot_mat, image.shape[1::-1], flags=cv2.INTER_LINEAR)
  return result