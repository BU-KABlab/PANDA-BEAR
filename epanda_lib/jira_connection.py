# Obtain an API token from: https://id.atlassian.com/manage-profile/security/api-tokens
# You cannot log-in with your regular password to these services.

from atlassian import Jira
from .config.secrets import JiraSecrets

epanda_jira = Jira(
    url=JiraSecrets.URL,
    username=JiraSecrets.USERNAME,
    password=JiraSecrets.PASSWORD,
    cloud=True)

projects = epanda_jira.projects()
for project in projects:
    print(f"Project: {project['name']} ({project['key']})")
    project_issues = epanda_jira.get_all_project_issues(project['key'])

    # from the project issues get the unique issue status types
    issue_statuses = set()
    for issue in project_issues:
        issue_statuses.add(issue['fields']['status']['name'])

    print(f"  Issue Types: {issue_statuses}")
    print(f"  Total Issues: {len(project_issues)}")
    print()

    # Get the unique users for each project
    all_users:dict = epanda_jira.users_get_all()
    unique_users = set()
    for user in all_users:
        user:dict
        if 'emailAddress' in user:
            unique_users.add(user['displayName'])

    print(f"  Unique Users: {unique_users}")
    print()
