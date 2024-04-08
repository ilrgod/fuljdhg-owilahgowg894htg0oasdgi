import base64
import json
import os
import glob
import time
import requests

host = "http://127.0.0.1:7860"
PROJECT_DIR = os.getcwd()
OUTPUT_DIR = f"{PROJECT_DIR}\images"

with open(f"{PROJECT_DIR}\config.json", 'r', encoding='utf-8') as f:
    CONFIG_JSON = json.load(f)

CONTROL_NODE = CONFIG_JSON.get('control_node_url')

progress = 0

requests.post(f'{host}/sdapi/v1/options', json={'samples_filename_pattern': '', 'directories_filename_pattern': 'images',
                    'outdir_img2img_samples': PROJECT_DIR, 'save_to_dirs': True, 'samples_format': 'jpg'})


def clear_images():
    for file in glob.glob(f'{PROJECT_DIR}/images/*.jpg'):
        for i in range(3):
            try:
                os.remove(file)
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
        print(j['task']['task_id'])
    else:
        print('ass')
    return response


def send_signal(task_id, status: str):
    data = dict(
        task_id=task_id,
        status=status,
        gpu_id=CONFIG_JSON.get('gpu_id'),
        secret_key=CONFIG_JSON.get('secret_key')
    )
    response = requests.post(f"{CONTROL_NODE}/send_signal", data=data)
    print(f'signal sent {status}')
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
    print(response.content)
    print('result sent')
    return response


def post_image(task):
    task_id = task['task_id']
    data = {"prompt": task["prompts"][0],
            "negative_prompt": task["prompts"][1],
            "cfg_scale": 6.5,
            "denoising_strength": 1,
            "steps": 35,
            "init_images": [task["image"]],
            "inpaint_full_res_padding": 32,
            "mask": task["mask"],
            "sampler_index": "DPM++ 2M Karras",
            "force_task_id": task_id,
            "save_images": True
            }

    clear_images()

    try:
        requests.post(f"{host}/sdapi/v1/img2img", json=data, timeout=1)
    except requests.exceptions.RequestException as e:
        pass
    except Exception as e:
        print('ERROR', str(e))

    send_signal(task_id, 'IN_PROGRESS')


def check_progress(task):
    global progress

    task_id = task['task_id']

    counter = 3

    success = False

    while counter:
        try:
            response = requests.get(f"{host}/sdapi/v1/progress?skip_current_image=false")

            new_progress = response.json().get('progress') or 0

            if new_progress > progress:
                print('growth')
                counter = 3
                send_signal(task_id, f'IN_PROGRESS')

            elif new_progress < progress or (new_progress == progress == 0):
                print('send res')
                files = glob.glob(f'{PROJECT_DIR}/images/*.jpg')
                if files:
                    file = files[0]
                    with open(file, 'rb') as img:
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
                            print('SEND WOOHOO')
                            break
                else:
                    counter -= 1

            time.sleep(1)
        except Exception as e:
            print('ERROR', str(e))
            counter -= 1

    if success:
        return

    if not counter:
        print(f'error task {task_id}')
        send_signal(task_id, 'ERROR')

    progress = 0


def main():
    while True:
        try:
            response = get_task()
            while response.json()['status'] != 200:
                print(response.json()['message'])
                response = get_task()
                time.sleep(0.5)

            task = response.json()['task']

            print('start post')
            post_image(task)
            time.sleep(1)
            print('start check progress')
            check_progress(task)
            print('end check progress')

        except Exception as e:
            print(str(e))


main()
