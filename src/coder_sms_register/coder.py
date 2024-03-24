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
    """A class used to manage users and workspaces via the Coder V2 API"""

    def __init__(self, coder_username: str):
        self.coder_username = coder_username

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
        

    def get_user_workspaces(self) -> list[list[str],list[str]]:
        """A method that fetches a coder user's workspaces and adds them as a property in the object instance"""

        url = os.environ.get("CODER_API_URL") + "workspaces?q=owner:" + self.coder_username

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Coder-Session-Token": os.environ.get("CODER_API_KEY")
        }
        
        if resp_body:= Coder.send_coder_request_with_retry(url, headers, 200, "GET", 3):
            logger.info(f"successfully fetched workspaces for user: {self.coder_username}")
            workspaces_list = [[],[]]
            if resp_body.get("count") == 0:
                logger.info(f"{self.coder_username} does not have any workspaces")
            else:
                for workspace in resp_body.get("workspaces"):
                    workspaces_list[0].append(workspace.get("id"))
                    if workspace.get("latest_build").get("status") == "stopped":
                        workspaces_list[1].append("stopped")
                    else:
                        workspaces_list[1].append("not stopped")
            
            self.workspaces = workspaces_list
            return workspaces_list
        
        else:
            logger.error(f"failed to fetch workspaces for user: {self.coder_username}")
            self.workspaces = None
            return None
    
    @staticmethod
    def delete_workspace(workspace_id) -> bool:
        """Static method to delete a Coder workspace via the V2 API"""

        url = os.environ.get("CODER_API_URL") + "workspaces/" + workspace_id + "/builds"

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Coder-Session-Token": os.environ.get("CODER_API_KEY")
        }

        req_body = {
            "orphan": False,
            "transition": "delete"
        }
        
        if resp_body:= Coder.send_coder_request_with_retry(url, headers, 201, "POST", 3, req_body):
            logger.info(f"successfully initated delete of workspace: {workspace_id}")
            return True
        
        logger.error(f"failed to initiate deletion of workspace: {workspace_id}")
        return False


    def remove_user_workspaces(self) -> bool:
        """
        A method to remove user workspaces
        
        Returns True if all workspaces are successfully removed or there aren't any workspaces to remove.
        Returns False if any worspace fails to be removed.
        """

        if self.get_user_workspaces() and self.workspaces[0]:
            if "not stopped" in self.workspaces[1]:
                logger.info(f"user {self.coder_username} has workspaces that are not stopped - cannot remove workspaces until they are stopped")
                return False
            
            else:
                workspace_remove_status = []
                for workspace in self.workspaces[0]:
                    if Coder.delete_workspace(workspace):
                        workspace_remove_status.append("removed")
                    else:
                        workspace_remove_status.append("not removed")
                
                if "not removed" in workspace_remove_status:
                    logger.error("could not remove all workspaces")
                    return False
                else:
                    logger.error("all workspaces removed")
                    return True
            
        else:
            logger.info("no workspaces to remove")
            return True
            

    def delete_coder_user(self) -> bool:
        """A method that deletes a Coder user via the V2 API"""
        
        url = os.environ.get("CODER_API_URL") + "users/" + self.coder_username

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Coder-Session-Token": os.environ.get("CODER_API_KEY")
        }
        
        if Coder.send_coder_request_with_retry(url, headers, 200, "DELETE", 3):
            logger.info(f"successfully deleted user: {self.coder_username}")
            return True
        else:
            logger.error(f"failed to delete user: {self.coder_username}")
            return False
    
    def remove_user(self) -> bool:
        """A method to remove the user set in the Coder object and their workspaces from the Coder server"""

        if self.remove_user_workspaces():
            # wait for 60 seconds for the workspaces to finish deleting before deleting the user
            sleep(60)

            if self.delete_coder_user():
                logger.info(f"{self.coder_username} successfully removed")
                return True
            else:
                logger.error(f"{self.coder_username} not successfully removed")
                return False
        else:
            logger.info(f"{self.coder_username} still has workspaces - we need to wait until they are deleted to remove the user")
            return False

    @staticmethod
    def send_coder_request_with_retry(url: str, headers: dict, success_status: int, http_method: str ="GET", attempts: int =3, req_body: dict =None) -> dict:
        """
            A static method that will attempt Coder API requests with retries in a backoff pattern. 

            Returns respond body json as dict if successful based on the success status code provided. Otherwise returns False.
        """
        for i in range(0, attempts):
            if resp_body:= Coder._send_user_coder_request(url, headers, success_status, http_method, req_body):
                return resp_body
            else:
                sleep(i ** 3 + .2) # sleep for .2, 1.2, 8.2, 27.2 ... seconds between retries
        
        # if we never complete a successful request in the number of attemptes allotted, return False
        return False 


    @staticmethod
    def _send_user_coder_request(url: str, headers: dict, success_status: int, http_method: str ="GET", req_body:dict =None) -> dict:
        """
            A private static method that executes Coder API requests.  

            http_method: must be "GET", "POST", or "DELETE".  

            Returns None if an exception occurs (SSL issue, timeout, etc). Returns False if any status code other than the success_status provided
            is returned from the API. Returns response body json as dict if the success_status provided is returned from the API.
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
            return resp.json()
        
        else:
            logger.error(f"problem with Coder API request - status code: {resp.status_code} - resp content: {resp.content}")
            return False

            

    

