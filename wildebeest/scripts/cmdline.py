import argparse
import argcomplete
from pathlib import Path

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

def main():
    p = argparse.ArgumentParser(description='Runs wildebeest commands')

    subparsers = p.add_subparsers(dest='subcmd')
    job_p = subparsers.add_parser('job', help='Run commands on wildebeest jobs')

    job_cmds = job_p.add_subparsers(help='Job commands', dest='jobcmd')
    job_run = job_cmds.add_parser('run', help='Run a wildebeest job specified by the yaml file')
    job_run.add_argument('job_yaml',
        help='Yaml file for the job to run',
        type=Path)

    argcomplete.autocomplete(p)
    args = p.parse_args()

    if args.subcmd == 'job':
        if args.jobcmd == 'run':
            # wdb job run
            import sys
            print(sys.argv)
            print(args.job_yaml)
            return run_job(args.job_yaml)
    else:
        print(f'Unhandled subcommand {args.subcmd}')
        return 1
