FROM ubuntu:20.04

ARG DEBIAN_FRONTEND=noninteractive

RUN apt update && apt install -y \
    python3.8 \
    python3-pip \
    git \
    cmake

# TODO: install llvm-features by default

# TODO: remove @BRANCH when I merge back to master
RUN pip install git+https://github.com/lasserre/wildebeest.git@docker-integration
