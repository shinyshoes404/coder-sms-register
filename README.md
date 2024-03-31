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


## Deploying

### Prerequisites
This application does not deploy with a single click. coder-sms-register provides the source code to build a docker image that can be deployed as a container. You will need to setup your own infrastructure and Twilio account and connect all of the components.  

__Before you get started, you need:__
 - A top level domain registered
    - An A record like __coder.yourdomain.com__ pointed toward your Coder instance (or the Nginx proxy server)
    - An A recored like __sms.yourdomain.com__ pointed toward the server that will run coder-sms-register (or the Nginx proxy server)
 - A Twilio account setup to recieve SMS messages
    - You will need to add the account SID and token your .env file before deploying
    - This is kind of a pain now for developers/hobbyists due to recent regulatory changes regarding Application to Person 10 Digit Long Code (A2P 10DLC)
    - The process takes at least a couple of days
    - The high level steps are:
        - Create a Twilio account and connect a payment method
        - Register a US A2P Sole Proprietor Brand
        - Register a new campaign and link to a messaging service (this is usually what takes the most time)
    - Links to more information on registering
        - [Direct Sole Proprietor Registration Overview](https://www.twilio.com/docs/messaging/compliance/a2p-10dlc/direct-sole-proprietor-registration-overview)
        - [A2P 10DLC Sole Proprietor Brands FAQ](https://help.twilio.com/articles/9550596959643-A2P-10DLC-Sole-Proprietor-Brands-FAQ)
    - The messaging service needs to be configured with a webhook URL 
 - A Coder instance deployed somewhere that is accessible on the public internet
    - Link to [Linux install instructions](https://coder.com/docs/v2/latest/install) from Coder
    - You will likely need to configure Nginx as a proxy and SSL endpoint either on the same machine or a separate machine
    - I recommend using Let's Encrypt for SSL, but you will need a wildcard certificate for all Coder feature to work, which will require DNS to verify you own the domain (no auto renewal with certbot). If you choose not to get a wildcard cert, you won't be able to use the port forward feature to view apps running in code-server.
    - Note: coder-sms-register requires that workspaces be stopped for a user before removing them. Be sure to set the schedule parameter in your template.
 - Somewhere to build the coder-sms-register docker image and deploy that is accessible from the public internet
    - Docker and docker compose will need to be installed
    - You will likely need to configure Nginx as a proxy and SSL endpoint either on the same machine or a separate machine

 ### Steps to deploy
 - Build the docker image
    - Clone this repository to the machine you will use to build the docker image
    - Move into the root of the project
    - Active docker build kit `export DOCKER_BUILDKIT=1`
    - Build the docker image `docker build --no-cache -t coder-sms-register .` (don't forget the `.` at the end)
    - You should now see __coder-sms-register__ listed when you run `docker images`
 - Update docker-compose.yml
    - You probably want to comment out the dns section
 - Create .env file
    - Make a copy of the .env-template file with the name .env `cp .env-template .env`
    - Open the .env file in an editor and update the variables for:
        - __Your Twilio account__
            - TWILIO_ACCOUNT_SID -> Found in your Twilio account and is used to verify that messages sent to the webhook url you configured in your messaging service are actually from Twilio
            - TWILIO_ACCOUNT_TOKEN -> Also found in your Twilio account and also used to verify inbound messages are coming from Twilio
            - TWILIO_AUTH_SID -> Used for sending sms messages. This can be the same as TWILIO_ACCOUNT_SID or based on a separate token you setup in your Twilio account.
            - TWILIO_AUTH_TOKEN -> Also used for sending sms messages. This can be the same as TWILIO_ACCOUNT_TOKEN or based on a separate token you setup in your Twilio account.
            - FROM_NUM -> The number you want sms messages to be sent from. This will have to be the phone number you connected to your messaging service in Twilio.
            - TWILIO_WEBHOOK_URL -> The endpoint Twilio sends your inbound sms messages to. This needs to match what you entered into the message service or phone number configuration in Twilio.
        - __coder-sms-register__
            - CODER_REG_LOG_LEVEL -> Make sure this is set to `info` and not `debug` before deploying to production
            - CODER_REG_ENV -> Make suer this is set to `prod` and not `dev` before deploying to production
            - CODER_EMAIL_DOM -> Coder requires an email address format for the username when logging into the web UI. The email address doesn't need to connect to a functioning mail server. The most logical value for this is the top level domain you registered.
            - CODER_API_URL -> The base url to access the Coder API. If the A record for reaching your Coder instance lists coder.yourdomain.com, then this value should be set to `coder.yourdomain.com/api/v2/`
            - CODER_API_KEY -> You will generate an API key from the Coder web UI using the admin account. This is what allows coder-sms-register to access the Coder API and create and delete users.
            - CODER_REG_PASS -> List the pass phrase you want user to send via text to receive a Coder login without space (not case sensitive). For example: If you wanted users to send the phrase 'I am ready to learn' via SMS to get their login you would list `iamreadytolearn` for this variable.
            - CODER_REMOVE_TIME -> How much time do you want to wait (in minutes) before automatically removing users and their workspaces. Note: All workspaces need to be stopped before a user can be removed. Be sure to setup your templates to stop workspaces after a set period of time. It would make sense for this value to be greater than the amount of time configured in template before automatically stopping workspaces.
            - CODER_CHECK_INTERVAL -> How frequently (in seconds) do you want to check for users that need to be removed.
        - __Redis__
            - REDIS_PW -> This is just for Redis running locally in the container. You can set this to whatever you want, but avoid spaces.
 - Start the container with `docker-compose up -d`


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