
from atlassian_tools.secrets import URL, USERNAME, PASSWORD
from atlassian import Jira
from atlassian_tools.kablab_projects import EPANDA_JIRA

jira = Jira(
    url=URL,
    username=USERNAME,
    password=PASSWORD,
    cloud=True)

issue_to_update = "EP-59"
issue = jira.issue(issue_to_update)
# for field in issue["fields"]:
#     print(f'{field} : {issue["fields"][field]}')

# Update the status of the issue
response = jira.set_issue_status(issue_to_update, EPANDA_JIRA.statuses.done.name)
print(response)