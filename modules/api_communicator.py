import base64

import requests

from modules.config import Config
from modules.utils import retry_on_connection_error

class APICommunicator:
    def __init__(self, config: Config):
        self.config = config
        self.host = "http://127.0.0.1:7860"

        self.set_options()


    @retry_on_connection_error
    def set_options(self):
        requests.post(f'{self.host}/sdapi/v1/options', json={
            'samples_filename_pattern': '',
            'directories_filename_pattern': 'images',
            'outdir_img2img_samples': self.config.project_dir,
            'save_to_dirs': True,
            'samples_format': 'jpg'})

    @retry_on_connection_error
    def get_task(self):
        response = requests.get(f"{self.config.control_node_url}/get_task", params={
            'gpu_id': self.config.gpu_id,
            'secret_key': self.config.secret_key
        })
        print("COMPLETE GET TASK")
        return response.json()

    @retry_on_connection_error
    def send_signal(self, task_id, status):
        requests.post(f"{self.config.control_node_url}/send_signal", data={
            'task_id': task_id,
            'status': status,
            'gpu_id': self.config.gpu_id,
            'secret_key': self.config.secret_key
        })

    @retry_on_connection_error
    def send_result(self, task_id, image_data):
        print('TRY SENDING RESULT')
        image_data_base64 = base64.b64encode(image_data).decode('utf-8')
        response = requests.post(f"{self.config.control_node_url}/send_result", data={
            'task_id': task_id,
            'image': image_data_base64,
            'gpu_id': self.config.gpu_id,
            'secret_key': self.config.secret_key
        })
        print("COMPLETE SEND RESULT")
        return response
