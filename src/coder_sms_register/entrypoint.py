from coder_sms_register.config import Config
from coder_sms_register.models import metadata_obj
from coder_sms_register.sms_listener import SMSListener
from coder_sms_register.sms_worker import SMSWorker
import sqlalchemy as db
from threading import Thread
from queue import Queue
from time import sleep
import redis

# Logging setup
import logging
logger = logging.getLogger(__name__)
logger.setLevel(Config.log_level)
logger.addHandler(Config.file_handler)
logger.addHandler(Config.stout_handler)




def main():
    """The main entrypoint function for coder sms register"""

    print("#########################################")
    print("###### STARTING CODER SMS REGISTER ######")
    print("#########################################")

    # create the database if it doesn't already exist
    engine = db.create_engine('sqlite:///' + Config.db_path)
    metadata_obj.create_all(engine)

    # create the queues that the threads will share
    inbound_sms_q = Queue()
    kill_q = Queue()
  
    # redis listener thread - listens for messages posted to the redis stream by the API
    # create the redis connection object
    redis_conn = redis.Redis(host=Config.redis_host, port=Config.redis_port, db=Config.redis_db, password=Config.redis_pw, decode_responses=True)
    # create the sms listener thread
    sms_listener_thread = Thread(target=SMSListener.get_message, args=[redis_conn, Config.redis_sms_stream_key, Config.redis_sms_consum_grp, "sms-listener-01", Config.redis_msg_read_count, Config.redis_block_time_ms, inbound_sms_q, kill_q])
    
    # thread to process incoming sms messages
    sms_proc_thread = Thread(target=SMSWorker.sms_worker, args=[kill_q, inbound_sms_q, engine])

    # start the threads
    sms_listener_thread.start()
    sms_proc_thread.start()

    # look for a keyboard interrupt (ctlr + c), so the app can be exited manually
    try:
        while True:
            sleep(5)
            logger.debug("coder sms register is running")
    except KeyboardInterrupt:
        for i in range (0,10):
            kill_q.put("kill")
        logger.warning("shutting down coder sms register")
    
    # collect all the threads before shutting down completely
    sms_listener_thread.join()
    sms_proc_thread.join()


if __name__ == "__main__":
    main()


