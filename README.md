# coder-sms-register
Allow users to sign up on a Coder server and recieve a username and temporary password.


## Setting Up Your Environment
 - `export $(grep -v '^#' .env | xargs)`


#### Build the Redis image and run the container
 - In order to conduct local end to end testing with the inbound API, you need a Redis stream available.
 - You can leverage multi-stage build to create a separate Redis image to use for development and testing that should behave exactly like it will in production.
 - Commands to build image and start Redis container
    - `export DOCKER_BUILDKIT=1` 
    - `docker build --no-cache --target redis_stage -t coder-sms-reg-redis-testing .`
    - Run container - assumes REDIS_PW environment variable is set in your dev environment
        - Gitbash in Windows: `docker run -itd -p 127.0.0.1:6379:6379 -e REDIS_PW=${REDIS_PW} coder-sms-reg-redis-testing:latest  //bin//ash -c 'redis-server --requirepass ${REDIS_PW} --daemonize yes  && ash'`
        - Linux: `docker run -itd -p 127.0.0.1:6379:6379 -e REDIS_PW=${REDIS_PW} coder-sms-reg-redis-testing:latest  //bin//ash -c 'redis-server --requirepass ${REDIS_PW} --daemonize yes  && ash'`