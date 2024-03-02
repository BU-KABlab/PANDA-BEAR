# Obtain an API token from: https://id.atlassian.com/manage-profile/security/api-tokens
# You cannot log-in with your regular password to these services.
from atlassian import Jira
from atlassian_tools.secrets import URL, USERNAME, PASSWORD
jira = Jira(
    url=URL,
    username=USERNAME,
    password=PASSWORD,
    cloud=True)
