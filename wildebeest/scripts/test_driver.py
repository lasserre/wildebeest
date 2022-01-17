from pathlib import Path
from subprocess import run
from wildebeest.buildsystemdrivers import CmakeDriver
from wildebeest import *
from wildebeest.runconfig import RunConfig
from wildebeest.postprocessing import *

from wildebeest.jobrunner import *
import time

def main():
    def do_task(x:Dict[str,Any]):
        count = x['count']
        taskname = x['name']
        throw_exc = x['throw']
        for i in range(count):
            print(taskname)
            time.sleep(0.5)

        if throw_exc:
            raise Exception(f'There was a problem in {taskname}!')

    workload = [
        Task('task1', do_task, {
            'count': 10,
            'name': 'Task 1 (10x)',
            'throw': False
        }),
        Task('task2', do_task, {
            'count': 15,
            'name': 'Task 2 (15x)',
            'throw': False
        })
    ]

    with JobRunner('test', workload, 10) as runner:
        runner.run()

if __name__ == '__main__':
    main()
