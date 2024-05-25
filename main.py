import base64
import json
import os
import shutil
import glob
import time
import requests
from requests.exceptions import ConnectionError


host = "http://127.0.0.1:7860"
PROJECT_DIR = os.getcwd()
OUTPUT_DIR = f"{PROJECT_DIR}\\images"

with open(f"{PROJECT_DIR}\\config.json", 'r', encoding='utf-8') as f:
    CONFIG_JSON = json.load(f)

CONTROL_NODE = CONFIG_JSON.get('control_node_url')

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

time.sleep(30)

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


def send_result(task_id, image_data: bytes):
    image_data_base64 = base64.b64encode(image_data).decode('utf-8')
    data = dict(
        task_id=task_id,
        image=image_data_base64,
        gpu_id=CONFIG_JSON.get('gpu_id'),
        secret_key=CONFIG_JSON.get('secret_key')
    )
    response = requests.post(f"{CONTROL_NODE}/send_result", data=data)
    print(f'COMPLETE SEND RESULT. ID: {task_id}\nSERVER RESPONSE: {response.content}')
    return response


def post_image(task):
    task_id = task['task_id']
    save_settings = {
        'directories_filename_pattern': str(task_id),
        'save_to_dirs': True,
        'samples_format': 'jpg'
    }
    data = {"prompt": task["prompts"][0],
            "negative_prompt": task["prompts"][1],
            "cfg_scale": 6.5,
            "denoising_strength": 1,
            "steps": 35,
            "init_images": [task["image"]],
            "inpaint_full_res_padding": 32,
            "mask": task["mask"],
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
                        r = send_result(task_id, img.read())

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
            response = get_task()
            while response.json()['status'] != 200:
                print(response.json()['message'])
                response = get_task()
                time.sleep(0.5)

            task = response.json()['task']

            print('START SETUP TASK TO IMG2IMG')
            post_status = post_image(task)
            time.sleep(1)
            if post_status:
                print('START CHECKING TASK PROGRESS')
                check_progress(task)
                print('END CHECKING TASK PROGRESS')

        except Exception as e:
            print(f'ERROR IN MAIN LOOP: {str(e)}')
            
        clear_images()


if __name__ == '__main__':
    main()
