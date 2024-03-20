import os, logging, sys
from logging.handlers import RotatingFileHandler


class Config:

    ### -- WHERE TO FIND FILES --- ###
    if os.environ.get("CODER_REG_ENV") == "dev":
        etc_basedir = os.path.abspath(os.path.dirname(__file__))
        etc_basedir = os.path.join(etc_basedir, '../../')
    
    else:
        etc_basedir = '/etc/coder-sms-register'
  
    db_path = os.path.join(etc_basedir, "coder_sms_register.db")

    ### --- LOG PARAMETERS --- ###
    # don't do debug level if running in a prod environament
    if os.environ.get("CODER_REG_LOG_LEVEL") == "debug" and os.environ.get("CODER_REG_ENV") == "dev":
        set_log_level = logging.DEBUG
    else:
        set_log_level = logging.INFO

    log_path = os.path.join(etc_basedir, "coder-sms-register.log")
    log_level = set_log_level
    log_format = logging.Formatter(" %(asctime)s - [%(levelname)s] - %(name)s - %(threadName)s - %(message)s", "%Y-%m-%d %H:%M:%S %z")
    log_maxbytes = 5000000
    log_backup_count = 1

    file_handler = RotatingFileHandler(log_path, maxBytes=log_maxbytes, backupCount=log_backup_count) 
    file_handler.setLevel(log_level)
    file_handler.setFormatter(log_format)

    stout_handler = logging.StreamHandler(sys.stdout)
    stout_handler.setLevel(log_level)
    stout_handler.setFormatter(log_format)

    # Logging setup
    logger = logging.getLogger(__name__)
    logger.setLevel(log_level)
    logger.addHandler(file_handler)
    logger.addHandler(stout_handler)

    ### -- TWILIO PARAMETERS --- ###
    twilio_url = "https://api.twilio.com/2010-04-01/Accounts"

    ### -- REDIS PARAMETERS --- ###
    redis_host = os.environ.get("REDIS_HOST")
    redis_port = int(os.environ.get("REDIS_PORT"))
    redis_pw = os.environ.get("REDIS_PW")
    redis_db = int(os.environ.get("REDIS_DB"))
    redis_sms_stream_key = "sms_stream"
    redis_sms_consum_grp = "sms_consum_grp"
    redis_msg_read_count = 3
    redis_block_time_ms = 1000