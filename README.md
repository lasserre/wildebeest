# wildebeest

Experiment runner that specializes in build system support and binary code analysis.

The idea for wildebeest came from my need to automate the process of building
several unrelated open source projects (hence the gnu inspiration in the name)
as an experiment. An experiment has a common algorithm for building each project in the
group of unrelated projects and will apply a group of common options, like
"use compiler X", "compile with debug info", "compile with this flag", etc.
So I need each project to accept my customizations for the experiment, but otherwise
compile correctly and with any project-specific options that are needed.

Putting all of this together resulted in the design of wildebeest, which hopefully
will help us achieve at least the following:

- Top-level control of the important experiment factors or variables
- Common/reusable build system support for thing like cmake, meson, and make
- Customizable experiment algorithms and hooks for processing at any stage
- Automation of the time-consuming/mind-numbing experiment build and processing
steps to reduce human error and improve sanity
