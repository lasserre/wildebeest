from pathlib import Path
from wildebeest.buildsystemdrivers import CmakeDriver
from wildebeest import *
from wildebeest.runconfig import RunConfig
from wildebeest.postprocessing import *

from wildebeest.jobrunner import *
from wildebeest.tasks.testing import do_test_task

def main():

    workload = [
        Task('task1', do_test_task, {
            'count': 10,
            'name': 'Task 1 (10x)',
            'throw': False
        }),
        Task('task2', do_test_task, {
            'count': 15,
            'name': 'Task 2 (15x)',
            'throw': False,
            # 'sleep': True
        }),
        Task('task3', do_test_task, {
            'count': 3,
            'name': 'Task 3 (15x)',
            'throw': True
        }),
    ]

    with JobRunner('test', workload, 10) as runner:
        runner.run()

if __name__ == '__main__':
    main()
