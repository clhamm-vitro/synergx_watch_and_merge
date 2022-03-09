# from sgx_files import save_persistent_data, load_persistant_data
# import os
#
# persistent_data_path = os.path.dirname(os.path.abspath(__file__)) + '/' + 'persistent_data.pkl'
# pd = load_persistant_data(persistent_data_path)
# pd['sequential_number'] = 736
# save_persistent_data(pd, persistent_data_path)

from sgx_files import SGX_folder
import cv2
watch_folder_path = 'C:\\Users\\glsp954\\Desktop\\Temporary\\SGX_save'
dest_image_folder = 'C:\\Users\\glsp954\\Desktop\\Temporary\\SGX_save'

watch_folder = SGX_folder(watch_folder_path=watch_folder_path,
                          dest_image_folder=dest_image_folder,
                          scan_rate=100)

old_file_list = watch_folder.get_file_list()

for f in old_file_list:
    print(f)
    file_path = watch_folder_path + "\\" + f
    image = cv2.imread(file_path)
    new_file_name = f[0:len(f)-3] + "png"
    new_file_path = watch_folder_path + "\\" + new_file_name
    cv2.imwrite(new_file_path, image)
