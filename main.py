from sgx_files import SGX_folder, SGX_identifiers, SGX_file, found_matching_files
from datetime import datetime

# Look for new file
# watch_folder_path = '\\\\10.53.9.16\\AutomaticExport'
watch_folder_path = 'C:\\Users\\glsp954\\Desktop\\Temporary\\SGX_watchfolder'
dest_image_folder = 'C:\\Users\\glsp954\\Desktop\\Temporary\\SGX_save'
# dest_image_folder = '\\\\10.53.9.16\\vitro_images'
# dest_image_folder = '\\\\10.53.9.115\\watch_test'

sgx_identifiers = SGX_identifiers(bf_id="", df_id="DF", cf_id="CF")
sgx_identifier_length = 2
file_extension_length = 3

watch_folder = SGX_folder(watch_folder_path=watch_folder_path,
                          dest_image_folder=dest_image_folder,
                          scan_rate=100)

# initialize old_file_list with whatever is in the watch folder
old_file_list = watch_folder.get_file_list()
print_count = 0
first_file = None
while True:
    current_file_list = watch_folder.get_file_list()
    if len(current_file_list) == 0:
        old_file_list = current_file_list
        if print_count == 0:
            print('watchfolder empty')
            print_count += 1
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
            sgx_file = SGX_file(newest_file, sgx_identifier_length, file_extension_length)
            if first_file is None:
                first_file = sgx_file
            elif found_matching_files(first_file, sgx_file):
                print('found a pair!')
                watch_folder.merge_images(first_file, sgx_file, sgx_identifiers)
                first_file = None
            else:
                print("oops, must have missed one...")
                first_file = sgx_file
            # watch_folder.process_file(newest_file)
            print_count = 0



