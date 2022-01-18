import argparse
import argcomplete
from pathlib import Path

from wildebeest.jobrunner import run_job

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
