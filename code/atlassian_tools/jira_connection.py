# Obtain an API token from: https://id.atlassian.com/manage-profile/security/api-tokens
# You cannot log-in with your regular password to these services.
from dataclasses import dataclass
from re import sub

from atlassian import Jira
from atlassian_tools.secrets import PASSWORD, URL, USERNAME

epanda_jira = Jira(
    url=URL,
    username=USERNAME,
    password=PASSWORD,
    cloud=True)

@dataclass
class Issue:
    expand: str
    id: str
    self: str
    key: str
    status: int
    priority: int
    subtask: bool
    subtasks: list
    # Add more fields as needed
