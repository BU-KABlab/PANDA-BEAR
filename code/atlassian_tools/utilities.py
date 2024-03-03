"""Classess and functions used to store and manipulate data from Jira and Confluence"""

from dataclasses import dataclass
from typing import List

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

@dataclass
class Status:
    """
    Represents a status of a ticket/isue.
    
    Attributes:
        id (int): The ID of the status.
        name (str): The name of the status.
    """

    id: int
    name: str

@dataclass
class Users:
    """
    Represents a user in the system.

    Attributes:
        accountID (str): The account ID of the user.
        emailAddress (str): The email address of the user.
        displayName (str): The display name of the user.
    """
    account_id: str
    email_address: str
    display_name: str

@dataclass
class Statuses:
    """
    Represents a collection of statuses for a project.

    Attributes:
        back_burner (Status): The back burner status.
        to_do (Status): The to-do status.
        in_progress (Status): The in-progress status.
        done (Status): The done status.
        blocked (Status): The blocked status.
    """
    back_burner: Status = None
    to_do: Status = None
    in_progress: Status = None
    done: Status = None
    blocked: Status = None

@dataclass
class Projects:
    """
    Represents a project in the system.
    
    Attributes:
        project_name (str): The name of the project.
        project_id (str): The ID of the project.
        project_key (str): The key of the project.
        statuses (Statuses): The statuses associated with the project.
        users (List[Users]): The users associated with the project.
    """
    project_name: str = None
    project_id: str = None
    project_key: str = None
    statuses: Statuses = None
    users: List[Users] = None
    issues: List[Issue] = None
