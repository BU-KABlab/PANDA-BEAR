# Obtain an API token from: https://id.atlassian.com/manage-profile/security/api-tokens
# You cannot log-in with your regular password to these services.
from dataclasses import dataclass
from re import sub

from atlassian import Jira
from config.secrets import Jira_Secrets

epanda_jira = Jira(
    url=Jira_Secrets.URL,
    username=Jira_Secrets.USERNAME,
    password=Jira_Secrets.PASSWORD,
    cloud=True)

@dataclass
class Issue:
    """This class is used to store the information from a Jira issue"""
    expand: str
    id: str
    self: str
    key: str
    status: int
    priority: int
    subtask: bool
    subtasks: list
    # Add more fields as needed
