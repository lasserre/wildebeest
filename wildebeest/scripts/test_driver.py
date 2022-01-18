from pathlib import Path
from wildebeest.buildsystemdrivers import CmakeDriver
from wildebeest import *
from wildebeest.runconfig import RunConfig
from wildebeest.postprocessing import *

from wildebeest.jobrunner import *
import time
from sys import stderr

def main():
    def do_task(x:Dict[str,Any]):
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

    workload = [
        Task('task1', do_task, {
            'count': 10,
            'name': 'Task 1 (10x)',
            'throw': False
        }),
        Task('task2', do_task, {
            'count': 15,
            'name': 'Task 2 (15x)',
            'throw': False,
            # 'sleep': True
        }),
        Task('task3', do_task, {
            'count': 3,
            'name': 'Task 2 (15x)',
            'throw': True
        }),
    ]

    with JobRunner('test', workload, 10) as runner:
        runner.run()

if __name__ == '__main__':
    main()

    # # test killing processes
    # import psutil
    # from psutil import TimeoutExpired
    # import subprocess

    # import os

    # def kill_descendent_processes(parent:psutil.Process):
    #     """Kills the children of parent recursively"""
    #     for ch in parent.children():
    #         if ch.children():
    #             kill_descendent_processes(ch)
    #         ch.kill()
    #         if ch in parent.children():
    #             # handle zombie process
    #             ch.wait(timeout=1)

    # pid = os.getpid()

    # p = subprocess.Popen(['sleep 30'], shell=True)
    # p2 = subprocess.Popen(['sleep 3'], shell=True)
    # # p2.returncode
    # # p2.pid

    # parent = psutil.Process(pid)
    # for c in parent.children(recursive=True):
    #     print(c)

    # # kill_descendent_processes(parent)
    # import IPython; IPython.embed()
