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

## Project Recipes
There are (or will be) a set of builtin project recipes in `projectrecipes`.
The idea is to allow custom recipes to be used, but for lack of a better place
to store the recipes I plan on using, I am including a set of builtin recipes
here. I could store them with my other experiment files, but I expect to use
recipes across different experiments, and they really are not experiment-specific.
