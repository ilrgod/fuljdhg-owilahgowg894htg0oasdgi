import os
from dotenv import load_dotenv
import json

load_dotenv()

print(os.environ.get('PROD_URL'))

mode = input('CHOOSE DAEMON MODE: "prod" or click enter if test: ')

try:

    with open('config.json', 'r') as file:
        config = json.load(file)

    if mode.strip().lower() == 'prod':
        config['control_node_url'] = os.getenv('PROD_URL')
        print('PROD')
    else:
        config['control_node_url'] = os.getenv('TEST_URL')
        print('TEST')


    with open('config.json', 'w') as file:
        json.dump(config, file)

    print('JSON HAVE BEEN CHANGED SUCCESSFULLY!')
except Exception as e:
    print(f'ERROR: {str(e)}')
finally:
    print('EDIT URL ENDED')

    with open('config.json', 'r') as file:
        config = json.load(file)

    print('CONTROL NODE URL SET TO', config['control_node_url'])
        
