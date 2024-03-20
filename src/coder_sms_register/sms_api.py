from coder_sms_register.config import Config
from flask import Flask, request, make_response
from flask_cors import CORS
import datetime, redis

from coder_sms_register.twilio import TwilioSignature

# Logging setup
import logging
logger = logging.getLogger(__name__)
logger.setLevel(Config.log_level)
logger.addHandler(Config.file_handler)
logger.addHandler(Config.stout_handler)

sms_api = Flask(__name__)

CORS(sms_api)


# gloabl var to keep track of redis consumer group issues
redis_cons_grp_status = "no error"

def _sms_msg_producer(msg: dict) -> bool:
    redis_conn = redis.Redis(host=Config.redis_host, port=Config.redis_port, db=Config.redis_db, password=Config.redis_pw, decode_responses=True)
    msg["received_datetime"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        redis_conn.xadd(Config.redis_sms_stream_key, msg, "*")
    except Exception as e:
        logger.error("problem publishing message to redis stream msg: {0}".format(msg))
        logger.error(e)
        return False
    
    return True


@sms_api.route("/inbound", methods=["POST"])
def inbound_sms():
    global redis_cons_grp_status
    if redis_cons_grp_status == "error":
        resp = make_response("internal server error", 500)
        return(resp)

    req_headers = request.headers
    twilio_sig = TwilioSignature(request, req_headers)

    if not twilio_sig.compare_signatures():
        resp = make_response("not authorized", 401)
        return resp
    
    req_data = request.form.to_dict()

    if not _sms_msg_producer(req_data):
        resp = make_response("internal server error", 500)
        return resp

    resp = make_response("<Response></Response>", 200)
    resp.headers["Content-Type"] = "text/html"
    return resp


