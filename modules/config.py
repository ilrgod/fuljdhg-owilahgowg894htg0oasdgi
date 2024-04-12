import json
import os

class Config:
    def __init__(self):
        self.project_dir = os.getcwd()
        self.output_dir = f"{self.project_dir}/images"
        with open(f"{self.project_dir}/config.json", 'r', encoding='utf-8') as f:
            self.config_json = json.load(f)
        self.control_node_url = self.config_json.get('control_node_url')
        self.gpu_id = self.config_json.get('gpu_id')
        self.secret_key = self.config_json.get('secret_key')
