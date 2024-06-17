"""
exceptions.py
Exceptions for the library.

MIT License:
Copyright (c) 2021 Florian Lapp

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation
files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy,
modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the
Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the
Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE
WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR
OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""

from .alarm_status import AlarmStatus

import abc

__all__ = [
    'Exception',
    'InternalException',
    'AddressException',
    'ModelException',
    'ChecksumException',
    'ChecksumRequestException',
    'ChecksumReplyException',
    'StateException',
    'StatusAlarmException'
]

class Exception(Exception, abc.ABC) :
    """Generic exception."""
    pass

class InternalException(Exception) :
    """
    Exception that indicates an internal error.

    This exception should never occur.
    """
    pass

class AddressException(Exception) :
    """Exception that indicates that an address is wrong."""
    pass

class ModelException(Exception) :
    """Exception that indicates that a model is wrong."""
    pass

class ChecksumException(Exception, abc.ABC) :
    """
    Exception that indicates that the checksum of a request or a reply is wrong.

    The reason for this exception is an unstable connection between the requester and the replier.
    """
    pass

class ChecksumRequestException(ChecksumException) :
    """
    Exception that indicates that the checksum of a request is wrong.

    The reason for this exception is an unstable connection from the requester to the replier.
    """
    pass

class ChecksumReplyException(Exception) :
    """
    Exception that indicates that the checksum of a reply is wrong.

    The reason for this exception is an unstable connection from the replier to the requester.
    """
    pass

class StateException(Exception) :
    """
    Exception that indicates that a function was invoked on an object when that object was in a
    state that prohibits the invocation of that function.
    """
    pass

class StatusAlarmException(Exception) :
    """Exception that indicates that an object is in an alarm status."""

    def __init__(self, alarm_status : AlarmStatus) -> None :
        """
        Constructs an exception.

        :param alarm_status:
            Alarm status of the object.
        """
        self.__alarm_status = alarm_status

    @property
    def alarm_status(self) -> AlarmStatus :
        """Gets the alarm status of the exception."""
        return self.__alarm_status