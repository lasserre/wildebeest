FROM ubuntu:20.04

ARG DEBIAN_FRONTEND=noninteractive

ARG USERNAME=testuser
ARG USER_UID=1000
ARG USER_GID=1000

# create a user with matching uid/gid inside docker so all our output files
# come out with the right permissions!
RUN groupadd -g ${USER_GID} ${USERNAME}
RUN useradd ${USERNAME} -u ${USER_UID} -g ${USER_GID} -m -s /bin/bash

#  http://www.gtlib.gatech.edu/pub/ubuntu/      << this went offline 5/21/24 (temporary? idk)
#  http://mirror.arizona.edu/ubuntu/

# RUN sed -i 's/archive.ubuntu.com/www.gtlib.gatech.edu\/pub/g' /etc/apt/sources.list
RUN sed -i 's/archive.ubuntu.com/mirror.arizona.edu/g' /etc/apt/sources.list
RUN apt update && apt install -y \
    python3.8 \
    python3-pip \
    git \
    cmake \
    ninja-build

# download public key for github.com
RUN mkdir -p -m 0600 ~/.ssh && ssh-keyscan github.com >> ~/.ssh/known_hosts

###############################################################
# FOR THIS TO WORK:
# - Add this to ~/.bashrc:
#       eval $(ssh-agent)
#       ssh-add ~/.ssh/id_rsa
#
# - Add this to ~/.bash_logout:
#       kill $SSH_AGENT_PID
#
# Refs:
# https://support.atlassian.com/bitbucket-cloud/docs/set-up-personal-ssh-keys-on-linux/
# https://kb.iu.edu/d/aeww
###############################################################

# How to forward ssh keys into docker: https://medium.com/@tonistiigi/build-secrets-and-ssh-forwarding-in-docker-18-09-ae8161d066

# don't need llvm-features right now...leave out unless/until we need it again
# (OLD) install llvm-features by default
# RUN --mount=type=ssh git clone git@github.com:lasserre/llvm-features.git

# don't need clang-dtlabels right now...leave out unless/until we need it again
# RUN --mount=type=ssh git clone git@github.com:lasserre/clang-dtlabels.git

# build LLVM lld
# for lld + clang use: -DLLVM_ENABLE_PROJECTS="clang;lld"
# RUN cd llvm-features && mkdir build && cd build && \
#     cmake -G Ninja -DLLVM_ENABLE_PROJECTS="lld" -DLLVM_TARGETS_TO_BUILD="X86" \
#             -DCMAKE_INSTALL_PREFIX=/llvm-build ../llvm && \
#     cmake --build . -j80 && \
#     cmake --install .

# build clang-dtlabels plugin
# RUN export Clang_DIR=/llvm-build && \
#     cd clang-dtlabels && mkdir build && cd build && \
#     cmake .. && \
#     cmake --build .

# ENV PATH="${PATH}:/llvm-build/bin"
