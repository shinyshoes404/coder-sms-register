from coder_sms_register.config import Config
import redis, queue

# Logging setup
import logging
logger = logging.getLogger(__name__)
logger.setLevel(Config.log_level)
logger.addHandler(Config.file_handler)
logger.addHandler(Config.stout_handler)


class SMSListener:
    
    @staticmethod
    def get_message(redis_conn: redis.Redis, redis_stream_key: str, redis_consumer_grp: str, consumer_name: str, msg_read_count: int, block_time_ms: int, inbound_sms_q: queue.Queue, kill_q: queue.Queue) -> None:
            
        try:
            redis_conn.xgroup_create(name=Config.redis_sms_stream_key, groupname=Config.redis_sms_consum_grp, mkstream=True, id="$")
            logger.info(f"created consumer group: {Config.redis_sms_consum_grp}")
        except redis.exceptions.ResponseError as e:
            if str(e) == "BUSYGROUP Consumer Group name already exists":
                logger.info(f"consumer group {Config.redis_sms_consum_grp} already exists - moving on")
            else:
                logger.error("problem creating consumer group in redis")
                logger.error(e)
                redis_cons_grp_status = "error"
        except Exception as e:
            logger.error("problem creating consumer group in redis")
            logger.error(e)
            redis_cons_grp_status = "error"


        while kill_q.empty():
            try:
                streams = redis_conn.xreadgroup(groupname=redis_consumer_grp, consumername=consumer_name, streams={redis_stream_key: ">"}, count=msg_read_count, block=block_time_ms)
            
            except Exception as e:
                logger.error(f"problem fetching message from redis with stream: {redis_stream_key} , consumer group: {redis_consumer_grp}, and consumer name: {consumer_name}")
                logger.error(e)
                streams = None
                
            if streams:
                logger.info(f"{len(streams[0][1])} messages retrieved from redis stream {streams[0][0]}")
                
                # loop through the messages and post them to the inbound sms queue, acknowledge the message with redis, and delete the message from the stream
                for msg in streams[0][1]:
                    logger.debug(f"posting this message to the sms_inbound_q: {msg[1]}")
                    inbound_sms_q.put(msg[1])

                    logger.debug(f"acknowledging message id in redis stream: {msg[0]}")
                    redis_conn.xack(redis_stream_key, redis_consumer_grp, msg[0])

                    logger.debug(f"deleting message from redis stream: {msg[0]}")
                    redis_conn.xdel(redis_stream_key, msg[0])