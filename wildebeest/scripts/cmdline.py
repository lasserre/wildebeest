import argparse
import argcomplete
from pathlib import Path

from wildebeest import Experiment, Job
from wildebeest import *
from wildebeest.jobrunner import run_job

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
# wdb log run2  # dumps job log for run 2, assume we are IN .exp folder (like git repo) - check for .wildebeest/exp.yaml
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
        print(f'{exp_folder} is not an experiment folder')
        return None
    return Experiment.load_from_yaml(exp_folder)

def cmd_create_exp(exp_folder:Path, name:str, projectlist=[]):
    try:
        exp = create_experiment(name, exp_folder=exp_folder, projectlist=projectlist)
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
    return run_job(job_yaml)

def cmd_show_lists():
    for pl in get_project_list_names():
        print(pl)
    return 0

def cmd_show_recipes(project_list=''):
    names = get_recipe_names() if not project_list else [r.name for r in get_project_list(project_list)]
    for name in names:
        print(name)
    return 0

def cmd_show_exps():
    for name in get_experiment_names():
        print(name)
    return 0

def main():
    p = argparse.ArgumentParser(description='Runs wildebeest commands')
    p.add_argument('--exp', type=Path, default=Path().cwd(), help='The experiment folder')

    subparsers = p.add_subparsers(dest='subcmd')

    create_p = subparsers.add_parser('create', help='Create instances of registered wildebeest experiments')
    create_p.add_argument('name', type=str, help='The registered name of the experiment to be created')
    create_p.add_argument('exp_folder', type=Path, default=None, help='The experiment folder', nargs='?')
    create_p.add_argument('-l', '--project-list', type=str, help='The name of the project list to use for this experiment')

    run_p = subparsers.add_parser('run', help='Run commands on wildebeest jobs')
    run_p.add_argument('-j', '--job', help='Job number to run', type=int)

    show_p = subparsers.add_parser('show', help='List information about requested content')
    show_p.add_argument('object', help='The object to show',
                        choices=['lists', 'recipes', 'exps', 'experiments'])
    show_p.add_argument('-l', '--project-list', type=str, help='For recipes, limits results to this project list')

    status_p = subparsers.add_parser('status', help='Show status of in-progress experiments')
    # status_p.add_argument

    # job_cmds = run_p.add_subparsers(help='Run commands', dest='runcmd')
    # job_run = job_cmds.add_parser('run', help='Run a wildebeest job specified by the yaml file')
    # job_run.add_argument('job_yaml',
    #     help='Yaml file for the job to run',
    #     type=Path)

    argcomplete.autocomplete(p)
    args = p.parse_args()

    if args.subcmd == 'create':
        name = args.name
        exp_folder = args.exp_folder if args.exp_folder else Path().cwd()/f'{name}.exp'
        proj_list = []
        if args.project_list:
            proj_list = get_project_list(args.project_list)
        return cmd_create_exp(exp_folder, name, proj_list)
    elif args.subcmd == 'run':
        # if args.runcmd == 'run':

        # wdb run -j N
        if 'job' in args:
            return cmd_run_job(args)

        # import IPython; IPython.embed()
        # return
    elif args.subcmd == 'show':
        if args.object == 'lists':
            return cmd_show_lists()
        elif args.object == 'recipes':
            pl = args.project_list if args.project_list else ''
            return cmd_show_recipes(pl)
        elif args.object == 'exps' or args.object == 'experiments':
            return cmd_show_exps()
    import sys
    print(f'Unhandled cmd-line: {sys.argv}')
    return 1

if __name__ == '__main__':
    main()
