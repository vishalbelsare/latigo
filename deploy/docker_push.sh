#!/bin/bash

# Adapted from https://github.com/equinor/gordo/blob/master/docker_push.sh

# Script to push an docker image to a docker registry. The docker image can
# either exist and be provided in the env variable DOCKER_IMAGE, or it will be
# built if DOCKER_IMAGE is empty and DOCKER_FILE is provided
#
# If $DOCKER_USERNAME is set then it will attempt to log in to the
# $DOCKER_REGISTRY using $DOCKER_USERNAME and DOCKER_PASSWORD, otherwise it
# assumes that you are already logged in.
#
# Pushes a docker image with name DOCKER_NAME, and tag tag with the 8 first
# chars of the git commit, and if the current commit is tagged it also pushes
# with those tags. So e.g. if git HEAD is commit "3f6f963" and with tag "0.0.2"
# then two tags are pushed, both "gordo-infrastructure/gordo-deploy:3f6f963" and
# "gordo-infrastructure/gordo-deploy:0.0.2" if DOCKER_NAME is
# "gordo-infrastructure/gordo-deploy".
#
# Expects the following environment variables to be set:
# DOCKER_FILE: Semi-Required. Dockerfile to build. Either DOCKER_IMAGE or
#              DOCKER_FILE must be set.
# DOCKER_NAME: Required. Docker name to push to.
# DOCKER_IMAGE: Semi-Required. The local docker image to push. Either
#               DOCKER_IMAGE or DOCKER_FILE must be set.
# DOCKER_USERNAME: If set then it uses it an the password to log in to the
#                  registry
# DOCKER_PASSWORD: If set then it uses it an the username to log in to the
#                  registry
# DOCKER_REGISTRY: Docker registry to push to. Defaults to
#                  auroradevacr.azurecr.io
# DOCKER_REPO: The docker repository of concern
# PROD_MODE: If false then pushed tags will include a -dev suffix.
#                  Defaults to false

DOCKER_NAME=$1
DOCKER_IMAGE=$2
IMAGE_VERSION=$3
tmp_tag="$(date +%Y-%m-%d)"

echo "Expected environment variables with values:"
echo " + DOCKER_FILE:      ${DOCKER_FILE}"
echo " + DOCKER_REGISTRY:  ${DOCKER_REGISTRY}"
echo " + DOCKER_REPO:      ${DOCKER_REPO}"
echo " + DOCKER_IMAGE:     ${DOCKER_IMAGE}"
echo " + DOCKER_NAME:      ${DOCKER_NAME}"
echo " + DOCKER_USERNAME:  ${DOCKER_USERNAME}"
echo " + DOCKER_PASSWORD:  NOT SHOWN"


if [[ -z "${DOCKER_NAME}" ]]; then
    echo "DOCKER_NAME must be set, exiting"
    exit 1
fi

if [[ -z "${DOCKER_REGISTRY}" ]]; then
    echo "DOCKER_REGISTRY must be set, exiting"
    exit 1
fi

if [[ -z "${DOCKER_REPO}" ]]; then
    echo "DOCKER_REPO must be set, exiting"
    exit 1
fi

if [[ -z "${IMAGE_VERSION}" ]]; then
    echo "IMAGE_VERSION must be set, exiting"
    exit 1
fi

if [[ -z "${DOCKER_USERNAME}" ]]; then
    echo "DOCKER_USERNAME not set: we assume that you are already logged in to the docker registry."
else
    # Logging in to the docker registry, exiting script if it fails
    echo "Logging in to docker registry ${DOCKER_USERNAME}@${DOCKER_REGISTRY}..."
    echo "${DOCKER_PASSWORD}" | docker login -u "${DOCKER_USERNAME}" --password-stdin "${DOCKER_REGISTRY}"
    if [ $? -eq 0 ]
    then
        echo "Logging in to docker registry ${DOCKER_USERNAME}@${DOCKER_REGISTRY}: OK"
    else
        echo "Logging in to docker registry ${DOCKER_USERNAME}@${DOCKER_REGISTRY}: Failed"
        exit 1
    fi
fi

if [[ -z "${DOCKER_IMAGE}" ]]; then
    if [[ -z "${DOCKER_FILE}" ]]; then
        echo "DOCKER_IMAGE or DOCKER_FILE must be provided, exiting"
        exit 1
    fi
    echo "building docker image $tmp_tag" 
    docker build -t "$tmp_tag"  -f $DOCKER_FILE .
    DOCKER_IMAGE="$tmp_tag"
fi

echo "Using version '$IMAGE_VERSION'"

if [[ -z "${PROD_MODE}" ]]; then
    echo "Skipping pushing of 'latest' image"
else
    # if we're in prod mode, we'll push the latest image.
    docker tag $DOCKER_IMAGE $DOCKER_REGISTRY/$DOCKER_REPO/$DOCKER_NAME:latest
    docker push $DOCKER_REGISTRY/$DOCKER_REPO/$DOCKER_NAME:latest
fi

docker tag $DOCKER_IMAGE $DOCKER_REGISTRY/$DOCKER_REPO/$DOCKER_NAME:$IMAGE_VERSION
docker push $DOCKER_REGISTRY/$DOCKER_REPO/$DOCKER_NAME:$IMAGE_VERSION

git tag --points-at HEAD | while read -r tag ; do
    docker tag $DOCKER_IMAGE $DOCKER_REGISTRY/$DOCKER_REPO/$DOCKER_NAME:$tag
    docker push $DOCKER_REGISTRY/$DOCKER_REPO/$DOCKER_NAME:$tag
done
