"""
Not to be committed to the repository.
This file contains the dataclasses for the projects in the KabLab JIRA.
"""
from .utilities import Status, Users, Projects, Statuses

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
