from coder_sms_register.config import Config
from queue import Empty, Queue
from coder_sms_register.twilio import TwilioSender
from coder_sms_register.models import users
from coder_sms_register.coder import Coder
from sqlalchemy.engine import Engine
from datetime import datetime
import sqlalchemy as db
import os, bcrypt

# Logging setup
import logging
logger = logging.getLogger(__name__)
logger.setLevel(Config.log_level)
logger.addHandler(Config.file_handler)
logger.addHandler(Config.stout_handler)


class MsgManager:
    """A class to process inbound sms messages, fetch and store data in the database, and send reply sms messages"""
    
    def __init__(self, phone_num: str, msg_body: str, db_engine: Engine):
        self.phone_num = phone_num
        self.msg_body = msg_body
        self.db_engine = db_engine
        self._check_from_num_format()

    def _check_from_num_format(self) -> None:
        """A private method to verify the phone number that sent the sms message is US based and is a 10 digit long code and set the object property accordingly"""
        if len(self.phone_num) != 12 or self.phone_num[:2] != "+1":
            self.phone_num_valid = False
            if len(self.phone_num) >= 12:
                self.phone_num = self.phone_num[:12]        
        else:
            self.phone_num_valid = True

        return None


    def gen_phone_hash(self) -> str:
        """A method to generate a hash from the phone number that sent the sms message using bcrypt, so we don't have to store the phone number in the database"""
          
        phone_num_bytes = self.phone_num.encode('utf-8') # converting phone number to array of bytes
        salt = bcrypt.gensalt() # generating the salt
        phone_num_hash = bcrypt.hashpw(phone_num_bytes, salt).decode("utf-8") # Hashing the phone number
        self.phone_num_hash = phone_num_hash

        return phone_num_hash

    def verify_pass_phrase(self) -> bool:
        """A method to check for a valid pass phrase in the sms message"""
        print("in verify")
        if self.msg_body.replace(" ", "").lower().rstrip(".").rstrip("!").rstrip("?") == os.environ.get("CODER_REG_PASS").replace(" ", "").lower():
            self.pass_verified = True
            print("set pass verified")
            logger.info("pass phrase matches")            
            return True
                
        self.pass_verified = False
        print(f"verify failed {self.msg_body}")
        print(f"env {os.environ.get('CODER_REG_PASS')}")
        return False
    
    def check_for_matching_user(self) -> str:
        """A method that checks the SQLite database to see if a user already exists for phone number that sent the message"""

        try:
            qry = db.select(users)
        
            with self.db_engine.connect() as connection:
                results_obj = connection.execute(qry)
                results_data = results_obj.fetchall()
        
        # if we have a problem fetching data from the database log the problem and return False
        except Exception as e:
            logger.error("problem getting users")
            logger.error(e)
            return False
        
        # if we don't have any users, no need to check anything
        if len(results_data) == 0:
            logger.info("no users found")
            return None
        
        # check the phone number against the existing hashes
        for user in results_data:            
            phone_num_bytes =  self.phone_num.encode('utf-8') # encoding user phone number              
            
            # if the phone number provided matches the bcrypt hash, return the username - note that we need to turn the has back into bytes before checking
            if bcrypt.checkpw(phone_num_bytes, user[0].encode("utf-8")): 
                return user[1]
                    
        return None

    def create_user(self) -> dict[str]:
        """A method to create a new Coder user and add them to the database."""

        creds = Coder.gen_credentials()

        if Coder.create_coder_user(creds["username"], creds["pw"]):
            if self._add_user_to_db(creds["username"], self.gen_phone_hash()):
                logger.info(f"user created and added to the database")

            else:
                logger.error(f"failed to save new Coder user {creds['username']} to database. Deleting user.")
                
                # attempt to remove the newly created user from Coder to avoid a mess with the data
                if Coder.delete_coder_user(creds['username']):
                    logger.info(f"Coder user {creds['username']} successfully deleted")
                else:
                    logger.error(f"failed to delete Coder user {creds['username']}")
                
                return None # created Coder user, but failed to store them in the database
            
            return creds # successfully created Coder user and stored them in database
        
        else:
            logger.error(f"failed to create new Coder user {creds['username']}")

            return None # failed to create the Coder user
        

    def _add_user_to_db(self, user_name: str, phone_hash: str) -> bool:
        """A private method to add a Coder user to the database."""
        
        try:
            qry = db.insert(users).values([phone_hash, user_name, datetime.now().strftime("%Y-%m-%d %H:%M:%S")])
            with self.db_engine.begin() as connection:
                connection.execute(qry)

        except Exception as e:
            logger.error("problem adding user to the database")
            logger.error(e)
            return None
        
        return True


class SMSWorker:
    """A class used to pick up inbound sms messages from the queue for processing"""

    @staticmethod
    def sms_worker(kill_q: Queue, inbound_sms_q: Queue, db_engine: Engine):
        """Method used to monitor a message queue and process sms messages passed into that queue"""

        while kill_q.empty():
            try:
                inbound_sms = inbound_sms_q.get(timeout=3)
                sms_msg = MsgManager(inbound_sms["From"], inbound_sms["Body"], db_engine) 
                if sms_msg.phone_num_valid:
                    print("check user")
                    existing_user = sms_msg.check_for_matching_user()
                    print("user checked")
                    if existing_user:
                        print("existing user")
                        logger.info(f"user {existing_user} already exists")
                    else:
                        print("verify pass phrase")
                        if sms_msg.verify_pass_phrase():
                            print("after verify")
                            logger.info(f"user does not exist and a correct pass phrase was provided. create a new user")
                            if user_creds:= sms_msg.create_user():
                                logger.info(f"successfully created new user")
                                ts = TwilioSender()
                                if ts.send_registration_sms(sms_msg.phone_num, sms_msg.phone_num_hash, user_creds["username"] + "@" + os.environ.get("CODER_EMAIL_DOM"), user_creds["pw"]):
                                    logger.info(f"credentials sent for {user_creds['username']}")
                                else:
                                    logger.error(f"failed to send credentials to {user_creds['username']}")
                            else: 
                                logger.error(f"problem creating new user")
                else:
                    logger.warning(f"invalid phone number received")         

            except Empty:
                logger.debug("sms inbound queue is empty")       
