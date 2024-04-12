from modules.task_manager import TaskManager
from modules.config import Config
from modules.api_communicator import APICommunicator
from modules.image_processor import ImageProcessor

if __name__ == '__main__':
    config = Config()
    communicator = APICommunicator(config)
    processor = ImageProcessor(config, communicator)
    processor.clear_images()
    manager = TaskManager(config, communicator, processor)
    manager.run()
