import os, base64, requests, hashlib, hmac
from coder_sms_register.config import Config
from datetime import datetime
from time import sleep
from textwrap import dedent

# Logging setup
import logging
logger = logging.getLogger(__name__)
logger.setLevel(Config.log_level)
logger.addHandler(Config.file_handler)
logger.addHandler(Config.stout_handler)

class TwilioSender:
    """Class for sending sms messages via Twilio's api"""

    def __init__(self):
        self.url = Config.twilio_url + "/" + os.environ.get("TWILIO_ACCOUNT_SID") + "/Messages.json"
        
        basic_auth = os.environ.get("TWILIO_AUTH_SID") + ":" + os.environ.get("TWILIO_AUTH_TOKEN")
        basic_auth_bytes = basic_auth.encode("utf-8")
        base64_bytes = base64.b64encode(basic_auth_bytes)
        base64_auth = base64_bytes.decode("ascii")

        self.headers = {"Authorization": "Basic " + base64_auth, "Content-Type": "application/x-www-form-urlencoded"}
        self.from_phone = os.environ.get("FROM_NUM")


    def send_registration_sms(self, phone_num: str, phone_num_hash: str, user_email: str, pw: str) -> bool:
        logger.info(f"attempting to send registration sms to {phone_num_hash}")
        body = dedent(f"""
            Here are your credentials for coder.handsonproduct.com
                      
            email: {user_email}

            pw: {pw}
            """.strip("\n"))

        if not self.send_sms_with_retry(2, body, phone_num):
            logger.error(f"failed to send sub sms to {phone_num_hash}")
            return False
        
        return True
 
 
    def send_sms(self, body: str, phone_num: str) -> bool:
        logger.info("attempting to send sms")
        
        req_body = {
            "Body": body,
            "To": phone_num,
            "From": self.from_phone
        }

        try:
            resp = requests.post(url=self.url, headers=self.headers, data=req_body)
        except requests.exceptions.Timeout:
            logger.warning("twilio request timed out")
            return None
        except requests.exceptions.SSLError:
            logger.warning("twilio request experienced an SSL error")
            return None
        except Exception as e:
            logger.error("twilio request encountered an unexpected error")
            logger.error(e)
            return None

        if resp.status_code != 201:
            logger.error("twilio request to send sms failed status code: {0} content: {1}".format(resp.status_code, resp.content))
            return None

        logger.info("sms message successfully sent")
        return True


    def send_sms_with_retry(self, attempts: int, body: str, phone_num: str) -> bool:
        # attempts = total attempts, not just retries
        for i in range(0, attempts):
            sms_result = self.send_sms(body, phone_num)
            if sms_result:
                return sms_result
            if i < max(range(0, attempts)):
                logger.warning("wait before we retry")
                sleep(1.5 + (i * 10))
                logger.warning("retrying twilio api call")
        logger.error("sms send exceeded the max number of attempts - max atempts: {0}".format(attempts))
        return None


class TwilioSignature:
    """Class used to verify inbound SMS message signatures from Twilio"""

    def __init__(self, request_body, headers: dict):
        self.request_body = request_body
        self.headers = headers
    
    def _get_header_sig(self) -> str:
        if self.headers.get("X-Twilio-Signature"):
            return self.headers.get("X-Twilio-Signature")        
        logger.warning("twilio signature header is missing")
        return None
    
    def _create_param_str(self) -> str:
        req_body_dict = self.request_body.form.to_dict()
        keys = list(req_body_dict.keys())
        keys.sort()
        param_str = ""
        for key in keys:
            param_str = param_str + key + req_body_dict.get(key)
        
        return param_str
    
    def _create_signature(self) -> str:
        key = bytes(os.environ.get("TWILIO_AUTH_TOKEN"), "UTF-8")
        contents = bytes(os.environ.get("TWILIO_WEBHOOK_URL") + self._create_param_str(), "UTF-8")
        hmac_obj = hmac.new(key, contents, hashlib.sha1)
        signature = hmac_obj.digest()
        # encode hmac signature to base64, then decode bytes to be a utf-8 string
        signature_base64_str = base64.b64encode(signature).decode('UTF-8')

        return signature_base64_str
    
    def compare_signatures(self) -> bool:
        header_signature = self._get_header_sig()
        if not header_signature:
            logger.warning("request signature does not match what is expected")
            return False
        
        if header_signature == self._create_signature():
            logger.info("request signature matches what is expected")
            return True
        
        return False
