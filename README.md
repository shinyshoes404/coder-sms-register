# coder-sms-register
coder-sms-register is an application that enables users to create credentials for a Coder server and receive a username and temporary password, all via SMS.

## Overview

### How it works
 - Users send a secret phrase via SMS to your Twilio messaging phone number
 - A random username and password to login to your Coder instance is created
 - The newly created credentials are sent back to the requesting phone number via SMS
 - The user logs into Coder, spins up a workspace, and starts to code
 - After a configurable amount of time, the user and their workspaces are automatically removed from Coder

### Intended use case
coder-sms-register was built with the intent of creating a seamless classroom coding lab experience for students and instructors.

Using Coder and code-server is a great way to quickly spin up preconfigured development environments for students allowing them to write code in their browser. No worries about Windows vs Mac. No hangups with dependencies not being installed.

__The Problem:__ Creating accounts and distributing credentials.

You could gather up emails for each of the students ahead of time, manually create accounts on your Coder instance, and distribute credentials on the day of the coding lab. That sounds like zero fun, and a lot of prep work. More prep work than writing this application? Probably not, but here we are. Instead, students can pull out the phones they were already looking at rather than listening to the lecture and text a secret phrase to a phone number, both of which you share when it's time to code. In a couple of minutes the students have received their credentials, logged in to Coder, and spun up their workspaces.

But, wait. After the class is over, I have manually delete all the users and workspaces that just got created. No, my friend. You don't! coder-sms-register will automatically remove the workspaces and users after a configured amount of time and purge the user data from the SQLite database. It's perfect!

### Tech components
 - Python for the main application
 - Python and Flask for the inbound SMS API
 - Redis stream as a message queue for inbound SMS
 - SQLite to track which phone numbers already have users and which users need to be cleaned up
 - Docker to package the application
 - Twilio as the SMS provider
 - Coder server accessible on the internet


## Developing

### Setting up your environment
 - Export the environment variables configured for local development `export $(grep -v '^#' .env | xargs)`

### Testing

#### Build the Redis image and run the container
 - To conduct local end to end testing with the inbound API, you need a Redis stream available.
 - You can leverage multi-stage build to create a separate Redis image to use for development and testing that should behave exactly like it will in production.
 - Commands to build image and start Redis container
    - `export DOCKER_BUILDKIT=1` 
    - `docker build --no-cache --target redis_stage -t coder-sms-reg-redis-testing .`
    - Run container - assumes REDIS_PW environment variable is set in your dev environment
        - Gitbash in Windows: `docker run -itd -p 127.0.0.1:6379:6379 -e REDIS_PW=${REDIS_PW} coder-sms-reg-redis-testing:latest  //bin//ash -c 'redis-server --requirepass ${REDIS_PW} --daemonize yes  && ash'`
        - Linux: `docker run -itd -p 127.0.0.1:6379:6379 -e REDIS_PW=${REDIS_PW} coder-sms-reg-redis-testing:latest  //bin//ash -c 'redis-server --requirepass ${REDIS_PW} --daemonize yes  && ash'`