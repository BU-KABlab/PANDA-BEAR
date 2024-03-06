"""
Not to be committed to the repository.
This file contains the dataclasses for the projects in the KabLab JIRA.
"""
from dataclasses import dataclass
from typing import List


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


EPANDA_JIRA = Projects(
    "ePANDA",
    "10004",
    "EP",
    Statuses(
        back_burner=Status(10015, "Back Burner"),
        in_progress=Status(10013, "In Progress"),
        to_do=Status(10012, "To Do"),
        done=Status(10014, "Done"),
    ),
    users = [
        Users("5ee7cb2b4784510aca5f3a62", None, "Harley Quinn"),
        Users("712020:89c896b4-a43d-439d-9edb-9b6b5709c381", "grobben@bu.edu", "Gregory Robben"),
        Users("712020:0beb4a9c-f7de-4db8-83cf-6a96fd7bbe16", "zhaoyiz@bu.edu", "zhaoyiz"),
    ]
)

EIS_JIRA = Projects(
    "Elliptical Imaging Station",
    "10002",
    "EIS",
    Statuses(
        in_progress=Status(10007, "In Progress"),
        to_do=Status(10006, "To Do"),
        done=Status(10008, "Done"),
    ),
)

MPA_JIRA = Projects(
    "MOF-Polymer Adsorption",
    "10003",
    "MPA",
    Statuses(
        in_progress=Status(10010, "In Progress"),
        to_do=Status(10009, "To Do"),
        done=Status(10011, "Done"),
    ),
)

PBF_JIRA = Projects(
    "Polar Bear Fur",
    "10001",
    "PBF",
    Statuses(
        to_do=Status(10003, "To Do"),
        in_progress=Status(10004, "In Progress"),
        done=Status(10005, "Done"),
    ),
)
