# from sgx_files import SGX_folder, load_old_gi_file_list, save_gi_file_list
from sgx_files import SGX_folder

# from sgx_image import assemble_images, get_list_of_images
# from upload_to_darwin import Darwin_uploader
# import os
#

""" Good Code """

# Look for new file
watch_folder_path = '\\\\10.53.9.16\\AutomaticExport'
# watch_folder_path = 'C:\\Users\\glsp954\\Desktop\\Temporary\\SGX_watchfolder'
gi_store_path = 'gi'
gi_unzip_path = 'gi_unzip'
# dest_image_folder = 'C:\\Users\\glsp954\\Desktop\\Temporary\\SGX_save'
# dest_image_folder = '\\\\10.53.9.16\\vitro_images'
dest_image_folder = '\\\\10.53.9.115\\watch_test'


watch_folder = SGX_folder(watch_folder_path=watch_folder_path,
                          dest_image_folder=dest_image_folder,
                          gi_store_path=gi_store_path,
                          gi_unzip_path=gi_unzip_path,
                          scan_rate=100)

# initialize old_file_list with whatever is in the watch folder
old_file_list = watch_folder.get_file_list()
print_count = 0
while True:
    current_file_list = watch_folder.get_file_list()
    if len(current_file_list) == 0:
        old_file_list = current_file_list
        print('watchfolder empty')
        watch_folder.sleep()
    else:
        new_files = watch_folder.check_for_new_files(old_file_list=old_file_list)
        if len(new_files) == 0:
            if print_count == 0:
                print('searching for new files...')
                print_count = 1
            watch_folder.sleep()
        else:
            # get the newest file
            new_files = sorted(new_files, reverse=True)
            newest_file = new_files[0]
            print('found new file {}'.format(newest_file))
            old_file_list = current_file_list
            watch_folder.process_file(newest_file)
            print_count = 0

""" Good Code """





# # assemble images

# if do_assemble_images:
#
#
#
#
# # upload images to darwin
# list_of_images = get_list_of_images(image_folder_path)
# if len(list_of_images) > 0 and upload_to_darwin:
#     darwin_uploader = Darwin_uploader()
#     darwin_uploader.upload(list_of_images)
#
# # remember the files we just process
# if load_old_file_list:
#     save_gi_file_list(current_file_list)
# # rinse, repeat