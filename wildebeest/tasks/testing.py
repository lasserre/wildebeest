from sys import stderr
import time
from typing import Any, Dict

def do_test_task(x:Dict[str,Any]):
    count = x['count']
    taskname = x['name']
    throw_exc = x['throw']
    for i in range(count):
        print(taskname)
        time.sleep(0.5)

    print('STD ERROR PRINT', file=stderr)

    if 'sleep' in x:
        time.sleep(5*60)    # 5 min

    if throw_exc:
        raise Exception(f'There was a problem in {taskname}!')
