import glob
import os
import time
from typing import Dict

import requests

from modules.api_communicator import APICommunicator
from modules.config import Config


class ImageProcessor:
    def __init__(self, config: Config, communicator: APICommunicator):
        self.config = config
        self.communicator = communicator
        self.progress = 0

    def clear_images(self):
        for file in glob.glob(f'{self.config.project_dir}/images/*.jpg'):
            try:
                os.remove(file)
            except:
                pass

    def post_image(self, task: Dict):
        self.clear_images()
        data = {
            "prompt": task["prompts"][0],
            "negative_prompt": task["prompts"][1],
            "cfg_scale": 6.5,
            "denoising_strength": 1,
            "steps": 35,
            "init_images": [task["image"]],
            "inpaint_full_res_padding": 32,
            "mask": task["mask"],
            "sampler_index": "DPM++ 2M Karras",
            "force_task_id": task["task_id"],
            "save_images": True,
            "override_settings": {
                "sd_model_checkpoint": "Reliberate_v3-inpainting"
            }
        }
        try:
            requests.post(f"{self.communicator.host}/sdapi/v1/img2img", json=data, timeout=1)
            self.communicator.send_signal(task['task_id'], 'IN_PROGRESS')
        except requests.exceptions.ReadTimeout:
            pass
        except requests.exceptions.RequestException as e:
            print('ERROR SET UP TASK TO IMG2IMG', str(e))

    def check_progress(self, task: Dict):
        task_id = task['task_id']
        counter = 3
        success = False
        while counter:
            try:
                response = requests.get(f"{self.communicator.host}/sdapi/v1/progress?skip_current_image=false")
                new_progress = response.json().get('progress') or 0
                if new_progress > self.progress:
                    print('PROGRESS GROWTH')
                    self.communicator.send_signal(task_id, 'IN_PROGRESS')
                elif new_progress < self.progress or (new_progress == self.progress == 0):
                    files = glob.glob(f'{self.config.project_dir}/images/*.jpg')
                    if files:
                        with open(files[0], 'rb') as img:
                            r = self.communicator.send_result(task_id, img.read())
                            result = r.json()
                            if result.get('status') == 200:
                                success = True
                                break
                            else:
                                counter -= 1
                    else:
                        counter -= 1
                self.progress = float(new_progress)
                time.sleep(1)
            except Exception as e:
                print('ERROR IN GET PROGRESS WHILE LOOP', str(e))
                counter -= 1
        if not success and not counter:
            print(f'ERROR IN TASK. ID: {task_id}')
            self.communicator.send_signal(task_id, 'ERROR')
            self.progress = 0
