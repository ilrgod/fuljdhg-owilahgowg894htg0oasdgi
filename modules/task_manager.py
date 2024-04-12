import time

from modules.config import Config
from modules.api_communicator import APICommunicator
from modules.image_processor import ImageProcessor

class TaskManager:
    def __init__(self, config: Config, communicator: APICommunicator, processor: ImageProcessor):
        self.config = config
        self.communicator = communicator
        self.processor = processor

    def run(self):
        while True:
            try:
                task = self.communicator.get_task()
                while task['status'] != 200:
                    print(task['message'])
                    task = self.communicator.get_task()
                    time.sleep(1)
                if task:
                    self.processor.post_image(task["task"])
                    self.processor.check_progress(task["task"])
            except Exception as e:
                print(f'ERROR IN MAIN LOOP: {str(e)}')

