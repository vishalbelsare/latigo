FROM python:3.7-stretch

# DISABLE pip cache and version check, increase the timeout, set some useful Python flags.
ENV PIP_NO_CACHE_DIR=off \
  PIP_DISABLE_PIP_VERSION_CHECK=on \
  PIP_DEFAULT_TIMEOUT=100 \
  PYTHONFAULTHANDLER=1 \
  PYTHONUNBUFFERED=1

RUN echo "APT::Get::Assume-Yes \"true\";" > /etc/apt/apt.conf.d/90assumeyes
RUN apt-get update && \
    apt-get upgrade && \
    rm -rf /var/lib/apt/lists/*

ARG HOME=/app
ARG USER_NAME=latigo
RUN mkdir -p $HOME
RUN groupadd -r -g 1337 $USER_NAME
RUN useradd -r -u 1337 -g $USER_NAME -d $HOME -s /sbin/nologin -c "$USER_NAME" $USER_NAME
RUN chown -R $USER_NAME:$USER_NAME $HOME
USER 1337
ENV HOME ${HOME}
ENV PATH="$HOME/.local/bin:${PATH}"

WORKDIR $HOME
COPY --chown=$USER_NAME:$USER_NAME app/requirements.txt ./
RUN pip install --user --upgrade pip
RUN pip install --user -r requirements.txt
COPY --chown=$USER_NAME:$USER_NAME app/ .
COPY --chown=$USER_NAME:$USER_NAME README.md app/VERSION LICENSE ./
COPY --chown=$USER_NAME:$USER_NAME deploy/ ./deploy
RUN python setup.py install --user
WORKDIR $HOME/latigo
