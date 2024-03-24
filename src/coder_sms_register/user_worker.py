from coder_sms_register.config import Config
from coder_sms_register.coder import Coder
from coder_sms_register.models import users
from queue import Queue
import sqlalchemy as db
from sqlalchemy.engine import Engine
from datetime import datetime, timedelta
from time import sleep
import os

# Logging setup
import logging
logger = logging.getLogger(__name__)
logger.setLevel(Config.log_level)
logger.addHandler(Config.file_handler)
logger.addHandler(Config.stout_handler)

class UserMgr:

    def __init__(self, db_engine: Engine):
        self.db_engine = db_engine

    def get_users(self) -> bool:
        """Method to fetch all users from the database and sets the users property of the UserMgr object.
        
        Returns True if no errors were encountered while fetching users. Returns False if an exception occurs."""

        self.users = None

        try:
            qry = db.select(users)
            
            with self.db_engine.connect() as connection:
                results_obj = connection.execute(qry)
                results = results_obj.fetchall()
        except Exception as e:
            logger.error("problem fetching users from the database")
            logger.error(e)
            return False
        
        user_list = []
        if len(results) == 0:
            logger.info("no users in the db")

        else:
            for row in results:
                user_list.append({"username": row[1], "create_stamp": row[2]})
            logger.info(f"fetched {len(user_list)} users from db")
            
        self.users = user_list       
        return True
        
    def delete_user(self, username: str) -> bool:
        try:
            qry = db.delete(users).where(users.c.username == username)
            with self.db_engine.begin() as connection:
                connection.execute(qry)
            
        except Exception as e:
            logger.error(f"problem deleting user: {username} from the db")
            logger.error(e)
            return False

        logger.info(f"user: {username} deleted from the db")
        return True
    

class UserWorker:
    """A class to house the method used to manage user removal from the Coder server"""

    @staticmethod
    def user_worker(kill_q: Queue, db_engine: Engine) -> None:
        """A static method that looks for users to remove from the coder server based on the configured interval set as an environment variable"""
        
        while kill_q.empty():
            logger.info("starting routine to check for Coder user that need to be deleted")
            user_mgr = UserMgr(db_engine)
            if user_mgr.get_users():
                removed_user_count = 0
                for user in user_mgr.users:
                    if datetime.strptime(user.get("create_stamp"), "%Y-%m-%d %H:%M:%S") + timedelta(minutes=int(os.environ.get("CODER_REMOVE_TIME"))) < datetime.now():
                        coder = Coder(user.get("username"))
                        if coder.remove_user():
                            logger.info("user removed from Coder server - now remove from db")
                            if user_mgr.delete_user(user.get("username")):
                                logger.info("user removed from db")
                                removed_user_count = removed_user_count + 1
                            else:
                                logger.error(f"user {user.get('username')} has been removed from the Coder server but is still in the db")
            if removed_user_count < 1:
                logger.info("no users removed")
            else:
                logger.info(f"{removed_user_count} users removed")

            sleep(int(os.environ.get("CODER_CHECK_INTERVAL")))
