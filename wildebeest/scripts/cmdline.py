import argparse
from datetime import datetime, timedelta
import shutil
from itertools import chain
import argcomplete
from pathlib import Path
import pandas as pd
from termcolor import colored
from typing import List, Tuple
from rich.console import Console
from rich.table import Table

from wildebeest import Experiment, ExpState
from wildebeest.jobrunner import Job, run_job
from wildebeest import *
from wildebeest.defaultbuildalgorithm import *
from wildebeest.run import RunStatus

# Other wdb command line examples/ideas:
# --------------------------------------
# YES, we can add sub-nouns like "wdb run status" but since we usually will
# be talking about experiments, let that be default/implied: "wdb [exp] status"
# --------------------------------------
# wdb create funcprotos ./fp.exp          # init registered experiment
# wdb create funcprotos fp.exp --project-list RANDOM
# wdb create funcprotos       # defaults to funcprotos.exp in cwd
# wdb run fp.exp                        # run an experiment with current project list
# wdb run fp.exp --project-list SPEC    # override project list
# wdb run fp.exp -j 25                  # run this with up to 25 jobs (runs) at once
# wdb kill fp.exp                       # TODO if needed
# wdb export fp.exp                     # TODO if needed, creates fp.exp.tar.gz?
# wdb export --data fp.exp              # exp definitions (exp.yaml), run status?, and data folder only
# wdb status            # show a status table of all running experiments (# runs complete/total # runs, # jobs, etc.)
# wdb status fp.exp     # more detailed status for this exp?
# wdb status fp.exp --run run1      # run status
# wdb log fp.exp run1               # dump the log from this run, we can combine with watch/tail to make this nice
# --------------------
# TODO let's design this like git - you run the commands FROM WITHIN EXP FOLDER
# to make the cmdline simpler...don't have to specify the experiment folder explicitly
# each time!
# ---------
# NOTE: create is the 1 command that is run from outside (like git clone)
# wdb create funcprotos [EXP_FOLDER}   # create funcprotos experiment, defaults to funcprotos.exp in cwd
# wdb create funcprotos -l|--project-list LIST  # create with specified list
# wdb log       # dump log for experiment (TODO: redirect this into a file as well...)
# wdb log 2     # dumps job log for run 2, assume we are IN .exp folder (like git repo) - check for .wildebeest/exp.yaml
# wdb log -j 4  # dump job log for job 4 (whichever run that is)
# // running
# wdb run       # runs the experiment
# wdb run -j 3  # runs job 3
# wdb run -r 1  # runs run 1??
# wdb status    # status table for this experiment
# wdb status run1   # status for a specific run
# wdb status -j 3   # status for job 3
# wdb set <key> <value>
    # wdb set projectlist NAME
# // listing/showing registered things
# wdb show lists
# wdb show recipes
# wdb show experiments

def get_experiment(args) -> Experiment:
    '''
    Determines the appropriate experiment folder for the command-line options and
    returns an Experiment instance (loaded from yaml) if possible. If not a valid
    experiment, returns None.
    '''
    exp_folder = args.exp
    if not Experiment.is_exp_folder(exp_folder):
        raise Exception(f'{exp_folder} is not an experiment folder')
    return Experiment.load_exp_from_yaml(exp_folder)

def cmd_create_exp(exp_folder:Path, name:str, projectlist=[], **kwargs):
    try:
        exp = create_experiment(name, exp_folder=exp_folder, projectlist=projectlist, **kwargs)
        exp.save_to_yaml()
    except Exception as e:
        print(e)
        return 1
    return exp is not None

def cmd_run_job(args):
    exp = get_experiment(args)
    if not exp:
        return 1

    if args.job is None:
        print('No job id specified')
        return 1

    job_yaml = Job.yamlfile_from_id(exp.workload_folder, args.job)
    return run_job(job_yaml, args.run_from_step, args.run_to_step)

def parse_run_numbers(run_numbers:str) -> List[Tuple]:
    try:
        rn_list = []
        for spec in run_numbers.split(','):
            if '-' in spec:
                speclist = spec.split('-')
                if len(speclist) != 2:
                    print(f'Error parsing spec {spec}')
                    return None
                start, stop = [int(x) for x in speclist]
                rn_list.append((start, stop))
            else:
                rn_list.append((int(spec),))
        return rn_list
    except:
        return None

def extract_run_numbers(run_spec:str) -> List[int]:
    '''
    Extracts the run numbers from the run_spec and returns
    a resulting equivalent list of expanded run numbers
    that are unique and sorted
    '''
    run_num_set = set()
    rn_list = parse_run_numbers(run_spec)
    for rspec in rn_list:
        if len(rspec) == 1:
            run_num_set.add(rspec[0])
        else:
            start, stop = rspec
            for i in range(start, stop+1):
                run_num_set.add(i)
    return sorted(list(run_num_set))

def cmd_run_exp(exp:Experiment, run_spec:str='', numjobs=1, force=False, run_from_step:str='',
        no_pre:bool=False, no_post:bool=False, buildjobs:int=None, debug:bool=False,
        debug_docker:bool=False):

    run_list = None
    if run_spec:
        exp_runs = exp.load_runs()
        if not exp_runs:
            exp_runs = exp.generate_runs()
        run_indices = [num-1 for num in extract_run_numbers(run_spec)]
        if run_indices[0] < 0 or run_indices[-1] >= len(exp_runs):
            print(f'Invalid run numbers specified')
            return 1
        print(f'Running the following runs: {run_spec}')
        run_list = [exp_runs[i] for i in run_indices]

    return exp.run(force=force, numjobs=numjobs, run_list=run_list,
                   run_from_step=run_from_step,
                   no_pre=no_pre, no_post=no_post, buildjobs=buildjobs,
                   debug_in_process=debug, debug_docker=debug_docker)

def cmd_docker_shell(exp:Experiment, run_number:int):
    matching_runs = [r for r in exp.load_runs() if r.number == run_number]
    if not matching_runs:
        print(f'Run number {run_number} does not exist in experiment at {exp.exp_folder}')
        return 1

    run = matching_runs[0]

    if not docker_is_running(run):
        if docker_container_exists(run):
            print(f'Restarting existing container...')
            docker_restart(run)
        else:
            print(f'Starting up the container...')
            docker_run(run)
    docker_attach_to_bash(run)
    docker_cleanup(run, {}, {})

    return 0

def cmd_ls_lists():
    for pl in get_project_list_names():
        print(pl)
    return 0

def cmd_ls_recipes(project_list=''):
    names = get_recipe_names() if not project_list else [r.name for r in get_project_list(project_list)]
    for name in names:
        print(name)
    return 0

def cmd_ls_exps():
    for name in get_experiment_names():
        print(name)
    return 0

def cmd_ls_alg(exp:Experiment, print_all:bool):
    if print_all and exp.algorithm.preprocess_steps:
        print('Preprocessing:')
        for pp in exp.algorithm.preprocess_steps:
            print(f'  {pp.name}')
        print()

    if print_all:
        print('Algorithm:')

    for s in exp.algorithm.steps:
        if print_all:
            print(f'  {s.name}')
        else:
            print(s.name)

    if print_all and exp.algorithm.postprocess_steps:
        print()
        print('Postprocessing:')
        for pp in exp.algorithm.postprocess_steps:
            print(f'  {pp.name}')
    return 0

def cmd_info_exp(exp1:Experiment):
    exp:Experiment = exp1

    print(f'{exp.name}')
    print(f'-----------------')
    # TODO print exp.description (implement)
    print()

    print(f'Algorithm Summary')
    print(f'-----------------')
    cmd_ls_alg(exp, True)
    print()

    print(f'Run Configs')
    print(f'-----------------')
    for rc in exp.runconfigs:
        print(rc.name)
    print()

    print(f'Project List')
    print(f'-----------------')
    print(f'Total # of projects: {len(exp.projectlist)}')
    shortlist = exp.projectlist[:10]
    for recipe in shortlist:
        print(f'  {recipe.name}')
    if len(shortlist) < len(exp.projectlist):
        print('  ...')
    print()

    print(f'Runs')
    print(f'-----------------')
    runs = exp.load_runs()
    num_runs = len(runs) if runs else len(exp.runconfigs) * len(exp.projectlist)
    print(f'Total # of runs = {num_runs}')
    return 0

def calc_inprogress_runtime(r:'Run') -> Tuple[timedelta, timedelta]:
    now = datetime.now()
    totalrt = now - r.starttime
    totalrt = timedelta(days=totalrt.days, seconds=totalrt.seconds)    # remove subsecond precision
    steprt = now - r.step_starttimes[r.current_step]
    steprt = timedelta(days=steprt.days, seconds=steprt.seconds)
    return steprt, totalrt

def calc_total_completed_runtime(r:'Run', step_rt:timedelta=None) -> timedelta:
    '''
    step_rt: In-progress step runtime, if applicable
    '''
    all_runtimes = list(r.step_runtimes.values())
    if step_rt:
        all_runtimes.append(step_rt)
    all_steps_rt = all_runtimes[0] if all_runtimes else timedelta(days=0, seconds=0)
    for x in all_runtimes[1:]:
        all_steps_rt += x
    all_steps_rt = timedelta(days=all_steps_rt.days, seconds=all_steps_rt.seconds)  # remove subsecond precision

    return all_steps_rt

run_formats = {
    RunStatus.RUNNING: 'bold cyan',
    RunStatus.READY: '',
    RunStatus.FAILED: 'bold red',
    RunStatus.FINISHED: 'bold green',
}

def cmd_status_exp(exp:Experiment):
    runs = exp.load_runs()
    for r in runs:
        if r.status == RunStatus.FINISHED:
            print(colored(f'Run {r.number} ({r.name}) - finished [{r.runtime}]', 'green'))
        elif r.status == RunStatus.FAILED:
            print(colored(f'Run {r.number} ({r.name}) - FAILED during "{r.current_step}" [{r.runtime}]', 'red', attrs=['bold']))
            print(colored(f'\t{r.error_msg}', 'red', attrs=['bold']))
        elif r.status == RunStatus.RUNNING:
            steprt, rt = calc_inprogress_runtime(r)
            print(f'Run {r.number} ({r.name}) running "{r.current_step}" [{steprt}] Total: [{rt}]')
        else:
            print(f'Run {r.number} ({r.name}) - {r.status}')

    # TODO: print summary numbers at bottom (Finished running 4 runs: 3/4 succeeded, 1/4 FAILED)
    # TODO add a -g option to group the output by category: (all running, all failed, all finished, all ready)
    # TODO add options to filter on subcategories: --failed, --done, --running, --ready
    # print(colored(f'[{j.task.name} FAILED]: {j.error_msg}', 'red', attrs=['bold']))
    return 0

def cmd_runtimes_exp(exp:Experiment):
    console = Console()
    runs = exp.load_runs()
    for r in runs:
        table = Table(title=f'{exp.name} Run {r.number} - {r.name}', header_style='default', title_style='default')
        table.add_column('Step')
        table.add_column('Runtime')

        highest_runtimes = sorted(r.step_runtimes.values(), reverse=True)
        steprt = None
        totalrt = r.runtime

        for s in exp.algorithm.steps:
            if s.name == r.current_step and r.status == RunStatus.RUNNING:
                steprt, totalrt = calc_inprogress_runtime(r)
                table.add_row(s.name, str(steprt), style='bold cyan')
            elif s.name in r.step_runtimes:
                fmt = ''
                if r.step_runtimes[s.name] == highest_runtimes[0]:
                    fmt = 'bold blue'
                elif r.step_runtimes[s.name] in highest_runtimes[1:4]:
                    fmt = 'bold yellow'
                elif s.name == r.current_step and r.status == RunStatus.FAILED:
                    fmt = 'bold red'
                tdprecise = r.step_runtimes[s.name]
                td = timedelta(days=tdprecise.days, seconds=tdprecise.seconds)
                table.add_row(s.name, str(td), style=fmt)
                # console.print(f'{fmt}{s.name}: {r.step_runtimes[s.name]}')
            else:
                table.add_row(s.name, '--')
                # console.print(f'{s.name}: --')

        # show total of current run (resets to zero if you restart from an intermediate step)
        current_total_fmt = 'bold cyan' if r.status == RunStatus.RUNNING else 'bold bright_black'
        table.add_section()
        table.add_row('Total (current run)', str(totalrt), style=current_total_fmt)

        # calculate a total of all completed steps
        all_steps_rt = calc_total_completed_runtime(r, steprt)

        total_fmt = 'bold bright_black'
        if r.status == RunStatus.FINISHED:
            total_fmt = 'bold green'
        elif r.status == RunStatus.FAILED:
            total_fmt = 'bold red'

        table.add_row('Total (all steps)', str(all_steps_rt), style=total_fmt)
        console.print(table)
    return 0

def cmd_dashboard(exp_parent_folder:Path):
    global run_formats

    console = Console()
    table = Table(title=f'wdb dashboard {exp_parent_folder}', header_style='default', title_style='default')
    table.add_column('Folder')
    table.add_column('Exp name')
    table.add_column('Run #')
    table.add_column('Run Name')
    table.add_column('Status')
    table.add_column('Runtime')
    table.add_column('Step Progress')
    table.add_column('Current Step')
    table.add_column('Step Runtime')
    table.add_column('Total Runtime')

    exp_folders = [exp_parent_folder] if Experiment.is_exp_folder(exp_parent_folder) else [x for x in exp_parent_folder.iterdir() if not x.is_file()]

    for exp_folder in sorted(exp_folders):
        if not Experiment.is_exp_folder(exp_folder):
            return
        exp = Experiment.load_exp_from_yaml(exp_folder)
        for r in sorted(exp.load_runs(), key=lambda r: r.number):
            fmt = run_formats[r.status]
            if r.status == RunStatus.RUNNING:
                step_rt, run_runtime = calc_inprogress_runtime(r)
            else:
                step_rt = '--'
                run_runtime = r.runtime
            step_num = exp.algorithm.get_index_of_step(r.current_step)+1 if r.current_step else 1
            num_steps = len(exp.algorithm.steps)
            step_prog = f'{step_num}/{num_steps} ({step_num/num_steps*100:.1f}%)'
            step_color = '[yellow]' if r.status == RunStatus.RUNNING else ''
            overall_rt_color = '[blue]' if r.status == RunStatus.RUNNING else ''

            folder_name = r.build.recipe.name if len(exp_folders) == 1 else exp_folder.name

            overall_rt = calc_total_completed_runtime(r, None if step_rt == '--' else step_rt)
            table.add_row(folder_name,
                        exp.name,
                        f'Run {r.number}',
                        r.config.name,
                        r.status,
                        str(run_runtime),
                        step_prog,
                        f'{step_color}{r.current_step}',
                        f'{step_color}{str(step_rt)}',
                        f'{overall_rt_color}{overall_rt}', style=fmt)

    console.print(table)
    return 0

def load_job_from_id(exp:Experiment, jobid:int) -> Job:
    yamlfile = Job.yamlfile_from_id(exp.workload_folder, jobid)
    return Job.load_job_from_yaml(yamlfile) if yamlfile.exists() else None

def cmd_kill_job(exp:Experiment, jobid:int, quiet:bool=False):
    job = load_job_from_id(exp, jobid)
    if not job:
        if not quiet:
            print(f'Job {jobid} yaml file not found')
        return 1
    job.kill()
    return 0

def cmd_kill_exp(exp:Experiment):
    runs = exp.load_runs()
    for jobid in range(len(runs)):
        # don't log missing jobs, we might have kicked off a subset of runs
        cmd_kill_job(exp, jobid+1, quiet=True)
    return 0

def cmd_job_log(exp:Experiment, jobid:int):
    job = None

    try:
        job = load_job_from_id(exp, jobid)
    except FileNotFoundError:
        print(f'Run {jobid} does not have a log')
        return 1

    with open(job.logfile, 'r') as f:
        for line in f.readlines():
            lower = line.lower()
            if 'failed during the' in lower or 'error during run' in lower:
                print(colored(line, 'red', attrs=['bold']), end='')
            else:
                print(line, end='')
    return 0

def cmd_rm_build(exp:Experiment, force:bool):
    if exp.build_folder.exists():
        if not force:
            print(colored(f'Are you sure you want to remove ', 'yellow', attrs=[]), end='')
            print(colored(f'ALL BUILD DATA??', 'red', attrs=['bold', 'underline', 'blink']), end='')
            print(f' ({exp.build_folder})')
            print(f'If so, rerun with -f')
            return 1

        shutil.rmtree(exp.build_folder)
        print(f'Removed build folder {exp.build_folder}')
        return 0
    else:
        print(f'No build folder at {exp.build_folder}')
        return 1

def main():
    p = argparse.ArgumentParser(description='Runs wildebeest commands')
    p.add_argument('--exp', type=Path, default=Path().cwd(), help='The experiment folder')

    subparsers = p.add_subparsers(dest='subcmd')

    # --- create: creates an experiment
    create_p = subparsers.add_parser('create', help='Create instances of registered wildebeest experiments')
    create_p.add_argument('name', type=str, help='The registered name of the experiment to be created')
    create_p.add_argument('exp_folder', type=Path, default=None, help='The experiment folder', nargs='?')
    create_p.add_argument('-l', '--project-list', type=str, help='The name of the project list to use for this experiment')
    create_p.add_argument('-r', '--recipe', type=str, help='The name of the recipe to use for this experiment (overrides -l)')
    create_p.add_argument('-p', '--params', nargs='+', help='Experiment-specific params to pass as-is to the experiment')

    # --- run: execute experiment/runs
    run_p = subparsers.add_parser('run', help='Run the experiment or specific runs/jobs')
    run_p.add_argument('run_numbers', nargs='?', type=str,
                        help='Subset of runs to execute (e.g. "1", "2-5", "1,4", "1,4-8,9-10")')
    run_p.add_argument('--job', help='Job number to run', type=int)
    run_p.add_argument('-j', '--numjobs', help='Number of parallel jobs to use while running', type=int, default=1)
    run_p.add_argument('-b', '--buildjobs', help='Number of jobs to use for each individual build (independent of --numjobs)',
                        type=int)
    run_p.add_argument('-f', '--force', help='Force running the experiment or job', action='store_true')
    run_p.add_argument('--from', dest='run_from_step', type=str, help='The step name to begin running (existing runs) from', default='')
    run_p.add_argument('--to', dest='run_to_step', type=str, help='The step name to run to (including this step)', default='')
    run_p.add_argument('--no-pre', help='Skip preprocessing steps', action='store_true')
    run_p.add_argument('--no-post', help='Skip postprocessing steps', action='store_true')
    run_p.add_argument('--debug', help='Run everything serially in-process for debugging', action='store_true')
    run_p.add_argument('--debug_docker', help='Start docker but kill experiment, leaving docker running to manually attach and debug builds',
                       action='store_true')

    # --- ls: List information
    ls_p = subparsers.add_parser('ls', help='List information about requested content')
    ls_p.add_argument('object', help='The object to list',
                        choices=['lists', 'recipes', 'exps', 'experiments', 'alg'])
    ls_p.add_argument('-l', '--project-list', type=str, help='For recipes, limits results to this project list')
    ls_p.add_argument('-a', '--all', help='For algorithms, print pre and post processing steps', action='store_true')

    # --- info: Show (composite) information about experiments/runs
    #           This is different from ls in that ls lists sequences of like things,
    #           info shows a variety of content
    info_p = subparsers.add_parser('info', help='Show info about requested content')

    # --- log: Show logs
    log_p = subparsers.add_parser('log', help='Show logs from experiment or runs/jobs')
    log_p.add_argument('run_number', help='The run number whose log should be shown', type=int, nargs='?')

    # --- status: Print experiment/run status
    status_p = subparsers.add_parser('status', help='Show status of in-progress experiments')
    # status_p.add_argument

    # --- dashboard: Print experiment/run status for all experiments in a folder
    dashboard_p = subparsers.add_parser('dashboard', help='Show status of all in-progress experiments')
    dashboard_p.add_argument('exp_parent_folder', help='Folder containing all experiments to be monitored')

    # --- runtimes: Print experiment step runtimes
    runtimes_p = subparsers.add_parser('runtimes', help='Show runtimes of experiment steps')

    # --- kill: Kill running jobs
    kill_p = subparsers.add_parser('kill', help='Kill experiments or jobs')
    kill_p.add_argument('--job', help='Job number to kill', type=int)
    kill_p.add_argument('-f', '--force', help='Force option required to kill entire experiment', action='store_true')

    # --- rm: Remove folders/artifacts from experiment
    rm_p = subparsers.add_parser('rm', help='Delete folders or artifacts from the experiment')
    rm_p.add_argument('object', help='The object to delete',
                       choices=['build'])
    rm_p.add_argument('-f', '--force', help='Force option required to remove experiment data', action='store_true')

    # --- docker_shell: Interact with a run's docker container
    docker_p = subparsers.add_parser('docker_shell', help='Attach to an interactive bash shell for a run\'s docker container')
    docker_p.add_argument('run_number', help='The run number whose docker container should be launched', type=int)

    # job_cmds = run_p.add_subparsers(help='Run commands', dest='runcmd')
    # job_run = job_cmds.add_parser('run', help='Run a wildebeest job specified by the yaml file')
    # job_run.add_argument('job_yaml',
    #     help='Yaml file for the job to run',
    #     type=Path)

    argcomplete.autocomplete(p)
    args = p.parse_args()

    # --- wdb create
    if args.subcmd == 'create':
        name = args.name
        exp_folder = args.exp_folder if args.exp_folder else Path().cwd()/f'{name}.exp'
        proj_list = []
        if args.recipe:
            # create custom list right here containing only the given recipe
            proj_list = [get_recipe(args.recipe)]
        elif args.project_list:
            proj_list = get_project_list(args.project_list)

        exp_kwargs = {k: v for k,  v in [p.split('=') for p in args.params]} if args.params else {}
        return cmd_create_exp(exp_folder, name, proj_list, **exp_kwargs)
    # --- wdb run
    elif args.subcmd == 'run':
        if args.job is not None:
            return cmd_run_job(args)
        return cmd_run_exp(get_experiment(args), args.run_numbers, args.numjobs, args.force, args.run_from_step,
                            no_pre=args.no_pre, no_post=args.no_post, buildjobs=args.buildjobs,
                            debug=args.debug, debug_docker=args.debug_docker)

    # --- wdb docker_shell
    elif args.subcmd == 'docker_shell':
        return cmd_docker_shell(get_experiment(args), args.run_number)

    # --- wdb ls
    elif args.subcmd == 'ls':
        if args.object == 'lists':
            return cmd_ls_lists()
        elif args.object == 'recipes':
            pl = args.project_list if args.project_list else ''
            return cmd_ls_recipes(pl)
        elif args.object == 'exps' or args.object == 'experiments':
            return cmd_ls_exps()
        elif args.object == 'alg':
            exp = get_experiment(args)
            return cmd_ls_alg(exp, args.all)
    elif args.subcmd == 'info':
        exp = get_experiment(args)
        return cmd_info_exp(exp)
    # --- wdb status
    elif args.subcmd == 'status':
        exp = get_experiment(args)
        return cmd_status_exp(exp)
    # --- wdb runtimes
    elif args.subcmd == 'runtimes':
        exp = get_experiment(args)
        return cmd_runtimes_exp(exp)
    # --- wdb dashboard
    elif args.subcmd == 'dashboard':
        return cmd_dashboard(Path(args.exp_parent_folder))
    # --- wdb kill
    elif args.subcmd == 'kill':
        exp = get_experiment(args)
        if args.job is not None:
            return cmd_kill_job(exp, args.job)
        if args.force:
            return cmd_kill_exp(exp)
        else:
            print(f'Are you sure you want to kill the experiment {exp.exp_folder}?')
            print(f'If so, rerun the command with the -f option')
            return 1
    # --- wdb log
    elif args.subcmd == 'log':
        exp = get_experiment(args)
        if args.run_number is not None:
            return cmd_job_log(exp, args.run_number)
    elif args.subcmd == 'rm':
        exp = get_experiment(args)
        if args.object == 'build':
            return cmd_rm_build(exp, args.force)
    import sys
    print(f'Unhandled cmd-line: {" ".join(sys.argv)}')
    p.print_help()
    return 1

if __name__ == '__main__':
    main()
