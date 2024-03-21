from coder_sms_register.config import Config
from time import sleep
import randomname, secrets, requests, os


# Logging setup
import logging
logger = logging.getLogger(__name__)
logger.setLevel(Config.log_level)
logger.addHandler(Config.file_handler)
logger.addHandler(Config.stout_handler)


class Coder:
    """A class used """

    @staticmethod
    def gen_credentials() -> dict[str]:
        """
            A static method that generates a random username and password to be used while creating a Coder user.
        
            Returns a dictionary with a randomly generated user name of the form <emotion>-<fish> and password.

            Example return value: {"username": "happy-tuna", "pw": "MG2kpRU91bo"}.
        """
        
        user_name = randomname.get_name(adj=('emotions',), noun=('fish',)) # generate a random user name of the form 'happy-tuna'
        pw = secrets.token_urlsafe(8) # generate a random password that will be about 10 characters in length

        return {"username": user_name, "pw": pw}
    
    @staticmethod
    def create_coder_user(user_name: str, pw: str) -> bool:
        """A static method that creates a Coder user via the V2 API"""

        url = os.environ.get("CODER_API_URL") + "users"

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Coder-Session-Token": os.environ.get("CODER_API_KEY")
        }

        req_body = {
            "disable_login": False,
            "email": user_name + "@" + os.environ.get("CODER_EMAIL_DOM"),
            "login_type": "password",
            "password": pw,
            "username": user_name
            }
        
        if Coder.send_coder_request_with_retry(url, headers, 201, "POST", 3, req_body):
            logger.info(f"successfully created user: {user_name}")
            return True
        else:
            logger.error(f"failed to create user: {user_name}")
            return False

    @staticmethod
    def delete_coder_user(user_name: str) -> bool:
        """A static method that deletes a Coder user via the V2 API"""
        
        url = os.environ.get("CODER_API_UR") + "users/" + user_name

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Coder-Session-Token": os.environ.get("CODER_API_KEY")
        }
        
        if Coder.send_coder_request_with_retry(url, headers, 200, "DELETE", 3):
            logger.info(f"successfully created user: {user_name}")
            return True
        else:
            logger.error(f"failed to create user: {user_name}")
            return False

    @staticmethod
    def send_coder_request_with_retry(url: str, headers: dict, success_status: int, http_method: str ="GET", attempts: int =3, req_body: dict =None) -> bool:
        """
            A static method that will attempt Coder API requests with retries in a backoff pattern. 

            Returns True if successful based on the success status code provided. Otherwise returns False.
        """
        for i in range(0, attempts):
            if Coder._send_user_coder_request(url, headers, success_status, http_method, req_body):
                return True
            else:
                sleep(i ** 3 + .2) # sleep for .2, 1.2, 8.2, 27.2 ... seconds between retries
        
        # if we never complete a successful request in the number of attemptes allotted, return False
        return False 


    @staticmethod
    def _send_user_coder_request(url: str, headers: dict, success_status: int, http_method: str ="GET", req_body:dict =None) -> bool:
        """
            A private static method that executes Coder API requests.  

            http_method: must be "GET", "POST", or "DELETE".  

            Returns None if an exception occurs (SSL issue, timeout, etc). Returns False if any status code other than the success_status provided
            is returned from the API. Returns True if the success_status provided is returned from the API.
        """

        # validate http method - raise exception if wrong
        if http_method not in ["GET", "POST", "DELETE"]:
            raise Exception("invalid http_methode provided - must be 'GET', 'POST', or 'DELETE'")
        
        try:
            if http_method == "GET":
                resp = requests.get(url=url, headers=headers, timeout=10)

            elif http_method == "POST":
                resp = requests.post(url=url, headers=headers, json=req_body, timeout=10)
            
            elif http_method == "DELETE":
                resp = requests.delete(url=url, headers=headers, timeout=10)

        except requests.exceptions.Timeout:
            logger.warning("Coder api request timed out")
            return None
        
        except requests.exceptions.SSLError:
            logger.warning("Coder api request experienced an SSL error")
            return None
        
        except Exception as e:
            logger.error("Coder api request encountered an unexpected error")
            logger.error(e)
            return None

        if resp.status_code == success_status:
            logger.info(f"Coder API request successful")
            return True
        
        else:
            logger.error(f"problem with Coder API request - status code: {resp.status_code} - resp content: {resp.content}")
            return False

            

    

