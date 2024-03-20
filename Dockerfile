# to build redis docker image for development and testing
# $ export DOCKER_BUILDKIT=1
# $ docker build --no-cache --target redis_stage -t coder-sms-reg-redis-testing .

# to build the production docker image
# $ export DOCKER_BUILDKIT=1
# $ docker build --no-cache -t coder-sms-register .


FROM python:3.11-alpine3.18 AS base


#### ---- ARGS AND ENVS FOR BUILD ---- ####

### - ENVS - ###

# default user
ENV USERNAME=coderreg
# set the python applications root directory
ENV PY_ROOT_DIR=/home/${USERNAME}/python_apps
# set the directory to store your python application
ENV PY_APP_DIR=${PY_ROOT_DIR}/coder_sms_register
# set app etc dir for log and db file
ENV ETC_DIR=/etc/coder-sms-register
# set the timezone info
ENV TZ=America/Chicago


#### ---- BASIC SYSTEM SETUP ---- ####

# update packages
# upgrade packages
# set timezone
# disable root user
# create our default user (this user will run the app)
RUN apk update && \
    apk upgrade && \
    cp /usr/share/zoneinfo/${TZ} /etc/localtime && \
    passwd -l root &&\
    $(adduser -D ${USERNAME}) 

FROM base AS redis_stage
# install redis
# update the bind directive in the redis config to allow outside hosts to access (for testing dev environment only)
RUN apk add redis && \
    sed -i -e 's/bind 127.0.0.1 ::1/bind 0.0.0.0/' /etc/redis.conf


FROM redis_stage AS python_stage

# set redis config back to bind to 127.0.0.1 for production use
RUN sed -i -e 's/bind 0.0.0.0/bind 127.0.0.1/' /etc/redis.conf

#### ---- PYTHON and APP ---- ####

# create directory for python app
# create etc directory for log files and db file
# use pip to install gunicorn (for api)
RUN mkdir -p ${PY_APP_DIR} && \
    mkdir -p ${ETC_DIR} && \
    pip install gunicorn

# copy the entire project into the container image, so we can install it
COPY ./ ${PY_APP_DIR}/

# move into the root of the project directory
# install the project using the setup.py file and pip
# remove the entire project
RUN cd ${PY_APP_DIR} && \
    pip install . && \
    rm -R ./*

# copy the file we need to run the api back into the image
COPY ./src/wsgi.py ${PY_APP_DIR}/

# upgrade packages after app install
RUN apk update && \
    apk upgrade

#### --- WHAT TO DO WHEN THE CONTAINER STARTS --- ####
#  make sure the default user owns the etc files so it can write logs and access the db file
# start redis (note: REDIS_PW is injected at run time)
# start the api with gunicorn and the coder sms register application
ENTRYPOINT chown -R ${USERNAME}:${USERNAME} ${ETC_DIR} && \
        chmod 700 ${ETC_DIR} && \
        redis-server --requirepass ${REDIS_PW} --daemonize yes && \
        su ${USERNAME} -c 'start-coder-sms-reg & cd ${PY_APP_DIR} && gunicorn --bind 0.0.0.0:8000 wsgi:sms_api'
