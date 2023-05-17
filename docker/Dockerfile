FROM ubuntu:20.04

ARG DEBIAN_FRONTEND=noninteractive

ARG USERNAME=testuser
ARG USER_UID=1000
ARG USER_GID=1000

# create a user with matching uid/gid inside docker so all our output files
# come out with the right permissions!
RUN groupadd -g ${USER_GID} ${USERNAME}
RUN useradd ${USERNAME} -u ${USER_UID} -g ${USER_GID} -m -s /bin/bash

#  http://www.gtlib.gatech.edu/pub/ubuntu/
RUN sed -i 's/archive.ubuntu.com/www.gtlib.gatech.edu\/pub/g' /etc/apt/sources.list
RUN apt update && apt install -y \
    python3.8 \
    python3-pip \
    git \
    cmake

# TODO: install llvm-features by default

# download public key for github.com
RUN mkdir -p -m 0600 ~/.ssh && ssh-keyscan github.com >> ~/.ssh/known_hosts

# 1. Set up ssh-agent on host machine: https://support.atlassian.com/bitbucket-cloud/docs/set-up-personal-ssh-keys-on-linux/
# 2. How to forward ssh keys into docker: https://medium.com/@tonistiigi/build-secrets-and-ssh-forwarding-in-docker-18-09-ae8161d066
RUN --mount=type=ssh git clone git@github.com:lasserre/llvm-features.git

# TODO: remove @BRANCH when I merge back to master
RUN pip install git+https://github.com/lasserre/wildebeest.git@docker-integration
