from darwin.client import Client

class Darwin_uploader:
    def __init__(self):
        self.API_KEY = 'nk-0F3R.W6shwsS8hbk0s6hSCTsvYyrxuBa8zFCO'
        self.client = Client.from_api_key(self.API_KEY)
        self.dataset_slug = "vitro-crestline-synergx"
        self.dataset_identifier = f"{self.client.default_team}/{self.dataset_slug}"
        self.dataset = self.client.get_remote_dataset(self.dataset_identifier)

    def upload(self, list_of_image_paths):
        self.dataset.push(list_of_image_paths)
