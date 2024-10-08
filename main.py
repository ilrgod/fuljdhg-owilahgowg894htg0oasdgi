import base64
import glob
import json
import os
import shutil
import time
from types import NoneType

from dotenv import load_dotenv

load_dotenv()

import requests
from requests.exceptions import ConnectionError

host = "http://127.0.0.1:7860"
PROJECT_DIR = os.getcwd()
OUTPUT_DIR = f"{PROJECT_DIR}\\images"

with open(f"{PROJECT_DIR}\\config.json", 'r', encoding='utf-8') as f:
    CONFIG_JSON = json.load(f)

CONTROL_NODE = CONFIG_JSON.get('control_node_url')
FS_HOST = "https://file-server.mmp.pw"
print(FS_HOST)


def add_file(filename, image_bytes, folder, mime_type='image/jpeg'):
    files = {
        'file_content': (filename, image_bytes, mime_type)
    }

    # Other form fields
    data = {
        'folder': folder,
        'filename': filename
    }

    retry = 5

    while retry:
        r = requests.post(f'{FS_HOST}/upload', data=data, files=files)

        if r.json().get('url'):
            image_url = r.json().get('url')
            return image_url

        retry -= 1

    if not retry:
        return None


def image_url_to_base64(image_url: str) -> str:
    # Fetch the image from the URL
    retries = 5

    response = None

    while retries:
        response = requests.get(image_url)

        if response.status_code == 200:
            break

        time.sleep(3)

        retries -= 1

    if not retries:
        response.raise_for_status()

    # Encode the image content to base64
    image_base64 = base64.b64encode(response.content).decode('utf-8')

    return image_base64


def get_lora_folder():
    try:
        response = requests.get(f'{host}/sdapi/v1/sd-models')
        r = response.json()

        return r[0]['filename'].split('models')[0] + "models\\Lora"
    except Exception as e:
        print(f'ERROR IN GET LORA FOLDER: {e}')

        return None


def get_required_loras():
    try:
        data = dict(
            gpu_id=CONFIG_JSON.get('gpu_id'),
            secret_key=CONFIG_JSON.get('secret_key')
        )

        response = requests.get(f'{CONTROL_NODE}/get_loras', params=data)

        return response.json()['loras']
    except Exception as e:
        print(f'ERROR IN GET REQUIRED LORAS: {e}')

        return None


def download_lora(lora_name):
    try:
        lora_folder = get_lora_folder()

        if not lora_folder:
            print(f'Lora folder not found')
            return False

        data = dict(
            gpu_id=CONFIG_JSON.get('gpu_id'),
            secret_key=CONFIG_JSON.get('secret_key'),
            filename=lora_name
        )

        response = requests.get(f'{CONTROL_NODE}/download_lora', params=data,
                                stream=True)
        response.raise_for_status()

        file_path = f'{lora_folder}/{lora_name}.safetensors'

        with open(file_path, 'wb') as file:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    file.write(chunk)

        print(f'File downloaded')
        return True

    except Exception as e:
        print(f'Error in downloading lora: {e}')
        return False


def get_downloaded_loras():
    try:
        response = requests.get(f'{host}/sdapi/v1/loras')
        r = response.json()

        return [lora["name"] for lora in r]
    except Exception as e:
        print(f'ERROR IN GET LORAS: {e}')

        return None


def get_missing_loras():
    required_loras = get_required_loras()
    print(required_loras)

    if not required_loras:
        return []

    downloaded_loras = get_downloaded_loras()
    print(downloaded_loras)

    missing_loras = [lora for lora in required_loras if lora not in downloaded_loras]

    return missing_loras


def refresh_loras():
    r = requests.post(f'{host}/sdapi/v1/refresh-loras')


def download_missing_loras():
    missing_loras = get_missing_loras()

    if isinstance(missing_loras, NoneType):
        print('GET MISSING LORAS ERROR')
    elif missing_loras == []:
        print('NO MISSING LORAS')
    else:
        print(f'MISSING LORAS: {len(missing_loras)}')

    for lora in missing_loras:
        status = download_lora(lora)
        if not status:
            break
    else:
        refresh_loras()
        return True

    return False


def loras_checks():
    refresh_loras()

    print('CHECKING LORAS')

    success = download_missing_loras()

    refresh_loras()

    return success


progress = 0
response = None
while not response:
    try:
        response = requests.post(f'{host}/sdapi/v1/options',
                                 json={'samples_filename_pattern': '',
                                       'outdir_img2img_samples': f'{PROJECT_DIR}\\images', 'save_to_dirs': True,
                                       'samples_format': 'jpg'})
    except Exception as e:
        print("ERROR IN SET OPTIONS. RETRY...")
        time.sleep(2)


# time.sleep(30)

def clear_images():
    for folder in os.listdir(f'{PROJECT_DIR}/images'):
        if folder != '.gitsave':
            for i in range(3):
                try:
                    shutil.rmtree(f'{PROJECT_DIR}/images/{folder}')
                    break
                except:
                    pass


def get_task():
    data = dict(
        gpu_id=CONFIG_JSON.get('gpu_id'),
        secret_key=CONFIG_JSON.get('secret_key')
    )
    response = requests.get(f"{CONTROL_NODE}/get_task", params=data)
    j = response.json()
    if j['status'] == 200:
        print("*" * 30)
        print(f"GET NEW TASK COMPLETE. ID: {j['task']['task_id']}")
    else:
        print("*" * 30)
        print(f'ERROR GET NEW TASK. CODE: {j["status"]}')
    return response


def send_signal(task_id, status: str):
    data = dict(
        task_id=task_id,
        status=status,
        gpu_id=CONFIG_JSON.get('gpu_id'),
        secret_key=CONFIG_JSON.get('secret_key')
    )
    response = requests.post(f"{CONTROL_NODE}/send_signal", data=data)
    print(f'COMPLETE SEND PROGRESS SIGNAL. CODE: {status}')
    return response


def send_result(task_id, image_data: bytes, filename):
    link = add_file(filename, image_data, 'ddcn_results')

    print(link)

    data = dict(
        task_id=task_id,
        image_link=link,
        gpu_id=CONFIG_JSON.get('gpu_id'),
        secret_key=CONFIG_JSON.get('secret_key')
    )

    response = requests.post(f"{CONTROL_NODE}/send_result", data=data)

    print(f'COMPLETE SEND RESULT. ID: {task_id}\nSERVER RESPONSE: {response.content}')

    return response


def post_image(task):
    task_id = task['task_id']

    print(task)

    b64_image = image_url_to_base64(task["image_url"])
    b64_mask = image_url_to_base64(task["mask_url"])

    save_settings = {
        'directories_filename_pattern': str(task_id),
        'save_to_dirs': True,
        'samples_format': 'jpg'
    }
    data = {"prompt": task["prompts"][0],
            "negative_prompt": task["prompts"][1],
            "cfg_scale": 6.5,
            "denoising_strength": 1,
            "steps": 30,
            "init_images": [b64_image],
            "inpaint_full_res_padding": 32,
            "mask": b64_mask,
            "sampler_index": "DPM++ 2M SDE",
            "force_task_id": task_id,
            "save_images": True,
            "override_settings": {
                "sd_model_checkpoint": "Reliberate_v3-inpainting",
                **save_settings
            }
            }

    clear_images()

    try:
        print(requests.post(f"{host}/sdapi/v1/img2img", json=data, timeout=1).json())
        send_signal(task_id, 'IN_PROGRESS')
        return True
    except requests.exceptions.RequestException as e:
        return True
    except Exception as e:
        print('ERROR SET UP TASK TO IMG2IMG', str(e))
        return False


def check_progress(task):
    global progress

    task_id = task['task_id']

    counter = 3

    success = False
    connection_error = False

    while counter:
        try:
            response = requests.get(f"{host}/sdapi/v1/progress?skip_current_image=false")

            new_progress = response.json().get('progress') or 0

            if new_progress > progress:
                print('PROGRESS GROWTH')
                counter = 3
                send_signal(task_id, 'IN_PROGRESS')

            elif new_progress < progress or (new_progress == progress == 0):
                print("PROGRESS NOT GROWTH")
                files = glob.glob(f'{PROJECT_DIR}/images/{str(task_id)}/*.jpg')
                if files:
                    file = files[0]
                    with open(file, 'rb') as img:
                        print('TRY SENDING RESULT')
                        r = send_result(task_id, img.read(), f'{str(task_id)}_{round(time.time())}.jpg')

                        clear_images()

                        print(r.json())

                        if not r.json():
                            print(r.content)
                            counter -= 1
                        elif r.json()['status'] != 200:
                            print(r.json())
                            counter -= 1
                        else:
                            success = True
                            print('!COMPLETE SEND RESULT!')
                            print("*" * 30)
                            break
                else:
                    counter -= 1

            progress = float(new_progress)

            time.sleep(1)
        except ConnectionError:
            connection_error = True
            break

        except Exception as e:
            print('ERROR IN GET PROGRESS WHILE LOOP', str(e))
            counter -= 1

    if success:
        return
    elif connection_error:
        print("CONNECTION ERROR. SD NOT WORKING.")
        print("PLEASE RUN STABLE DIFFUSION")

    if not counter:
        print(f'ERROR IN TASK. ID: {task_id}')
        send_signal(task_id, 'ERROR')

    progress = 0


def main():
    while True:
        clear_images()

        try:
            requests.post(f"{host}/")
        except Exception as e:
            print(f'SD CONNECTION ERROR: {e}')
            continue
        try:
            while True:
                success = loras_checks()

                if success:
                    response = get_task()

                    if response.json()['status'] == 200:
                        break
                    else:
                        print(response.json()['message'])
                        time.sleep(0.3)
                else:
                    print('UNABLE TO UPDATE LORAS')
                    time.sleep(0.5)
                    continue

            task = response.json()['task']

            print('START SETUP TASK TO IMG2IMG')
            try:
                post_status = post_image(task)
            except Exception as e:
                print(f'SETUP TASK ERROR: {e}')
                send_signal(task['task_id'], 'ERROR')

            time.sleep(1)
            if post_status:
                print('START CHECKING TASK PROGRESS')
                check_progress(task)
                print('END CHECKING TASK PROGRESS')
        except Exception as e:
            print(f'ERROR IN MAIN LOOP: {str(e)}')
            time.sleep(0.5)

        clear_images()


if __name__ == '__main__':
    main()
