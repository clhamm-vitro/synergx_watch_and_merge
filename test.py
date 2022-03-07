from sgx_files import assemble_images

# from sgx_files import SGX_folder, load_old_gi_file_list, save_gi_file_list
from sgx_files import SGX_folder
from sgx_image import show_image

# from sgx_image import assemble_images, get_list_of_images
# from upload_to_darwin import Darwin_uploader
# import os
#

""" Good Code """

# Look for new file
# watch_folder_path = '\\\\10.53.9.16\\AutomaticExport'
watch_folder_path = 'C:\\Users\\glsp954\\Desktop\\Temporary\\SGX_watchfolder'
gi_store_path = 'gi'
gi_unzip_path = 'gi_unzip'
dest_image_folder = 'C:\\Users\\glsp954\\Desktop\\Temporary\\SGX_save'
# dest_image_folder = '\\\\10.53.9.16\\vitro_images'
# dest_image_folder = '\\\\10.53.9.115\\watch_test'


watch_folder = SGX_folder(watch_folder_path=watch_folder_path,
                          dest_image_folder=dest_image_folder,
                          gi_store_path=gi_store_path,
                          gi_unzip_path=gi_unzip_path,
                          scan_rate=100)

image_BF, image_DF, image_combined = assemble_images(gi_unzip_path=watch_folder.gi_unzip_path,
                                                             dest_image_folder=watch_folder.dest_image_folder)


