
from atlassian_tools.jira_connection import epanda_jira, Issue
from atlassian_tools.kablab_projects import EPANDA_JIRA

issue:dict = epanda_jira.issue('EP-59')
for key, value in issue.items():
    print(f"{key}: {value}")
    if key == "fields":
        for field, field_value in value.items():
            print(f"\t{field}: {field_value}")
