import time
import serial
import typing
import binascii
import re
import time
import enum
import threading
from .mill_port import Port



class Mill_Control:
    '''Set up the mill connection and pass commands, including special commands'''
    def __init__(
        self,
        port : Port,
    ) -> None :
        """
        Constructs a Mill.

        :param port:
            Port the Mill is connected to.
        """
  
        self.__port = port
        self.__port_lock = threading.Lock()
        self.__safe_mode = False
        self.__heartbeat_thread : typing.Optional[threading.Thread] = None
        self.__heartbeat_event : typing.Optional[threading.Event] = None
        self.__heartbeat_event_timeout = 0.0 

    
    def __init__(self,port: Port ) -> None:
        
       
        self.ser_mill = serial.Serial(
            port= 'COM6',
            baudrate=115200,
            
            )
        if not self.ser_mill.isOpen():
            self.ser_mill.open()
        time.sleep(2)
    def send_to_mill(self,command:str):
        '''INPUT:
        command: "command to send"
        ser: serial variable for the mill
        OUTPUT: Returns the response from the mill'''
        ser = self.ser_mill
        if command != 'close':
            print(f'Sending: {command.strip()}')
            ser.write(str(command+'\n').encode())
            time.sleep(1)
            out=''
            while ser.inWaiting() > 0:
                out = ser.readline()
                        
            if out != '':
                response = (out.strip().decode())
        else:
            ser.close()
            time.sleep(15)    
        return response
    
    def stop(self):
        '''Stop the mill'''
        Mill_Control.send_to_mill('$X')
    def reset(self):
        Mill_Control.send_to_mill('(ctrl-x)')
    def home(self):
        Mill_Control.send_to_mill('$H')
    def current_status(self):
        Mill_Control.send_to_mill('?')
    def gcode_mode(self):
        Mill_Control.send_to_mill('$C')
    def gcode_paramaters(self):
        Mill_Control.send_to_mill('$#')
    def gcode_parser_state(self):
        Mill_Control.send_to_mill('$G')
    
    def __heartbeat_setup(self, timeout_seconds : float) -> None :
        activate = timeout_seconds != 0
        active = self.__heartbeat_thread is not None
        self.__heartbeat_event_timeout = timeout_seconds / 2
        if activate == active :
            if activate :
                self.__heartbeat_event.set()
            return
        if activate :
            self.__heartbeat_thread = threading.Thread(
                target = self.__heartbeat,
                daemon = True
            )
            self.__heartbeat_event = threading.Event()
            self.__heartbeat_thread.start()
        else :
            self.__heartbeat_event.set()
            self.__heartbeat_thread.join()
            self.__heartbeat_event = None
            self.__heartbeat_thread = None

    def __heartbeat(self) -> None :
        while self.__heartbeat_event_timeout != 0.0 :
            if self.__heartbeat_event.wait(self.__heartbeat_event_timeout) :
                self.__heartbeat_event.clear()
            else :
                self.__command_transceive(Pump.__CommandName.STATUS)



class Mill :
    """Mill."""

    def __init__(
        self,
        port : Port,
    ) -> None :
        """
        Constructs a Mill.

        :param port:
            Port the Mill is connected to.
        """
  
        self.__port = port
        self.__port_lock = threading.Lock()
        self.__safe_mode = False
        self.__heartbeat_thread : typing.Optional[threading.Thread] = None
        self.__heartbeat_event : typing.Optional[threading.Event] = None
        self.__heartbeat_event_timeout = 0.0 

    @property
    def status(self) -> Status :
        """Gets the status of the pump."""
        status, _ = self.__command_transceive(Pump.__CommandName.STATUS)
        return status

    @property
    def running(self) -> bool :
        """Gets if the pump is running."""
        return self.status in [Status.INFUSING, Status.WITHDRAWING, Status.PURGING]

    # Start transmission
    __STX = 0x02
    # End transmission
    __ETX = 0x03


    def __argument_str(value : str) -> str :
        return value

    def __argument_int(value : int) -> str :
        return str(value)

    def __argument_float(value : float) -> str :
        # From the docs: Maximum of 4 digits plus 1 decimal point. Maximum of 3 digits to the right
        # of the decimal point.
        if value.is_integer() :
            return str(int(value))
        value_string = str(value)
        if len(value_string) > 5 :
            value_string = value_string[0 : 5]
        return value_string

    __ARGUMENT = {
        str   : __argument_str,
        int   : __argument_int,
        float : __argument_float
    }

    @staticmethod
    def __command_checksum_calculate(data : bytes) -> int :
        """Gets the CCITT-CRC of the given data."""
        return binascii.crc_hqx(data, 0x0000)

    @staticmethod
    def __command_request_format(
        address : int,
        name : __CommandName,
        arguments : typing.Iterable[typing.Union[str, int, float]] = []
    ) -> str :
        return str(address) + name.value + ''.join(
            Pump.__ARGUMENT[type(argument)](argument)
            for argument in arguments
        )

    @classmethod
    def __command_reply_parse(
        cls,
        address : int,
        data_string : str
    ) -> typing.Tuple[Status, typing.Optional[AlarmStatus], str] :
        data_length = len(data_string)
        if data_length < 3 :
            raise InternalException()
        address_string = data_string[0 : 2]
        address_ = int(address_string)
        if address_ != address :
            raise AddressException()
        status_string = data_string[2]
        if status_string == cls.__STATUS_ALARM :
            if data_string[3] != '?' :
                raise InternalException()
            alarm_status_string = data_string[4]
            alarm_status = cls.__ALARM_STATUS.get(alarm_status_string)
            if alarm_status is None :
                raise InternalException()
            return Status.STOPPED, alarm_status, ''
        status = cls.__STATUS.get(status_string)
        if status is None :
            raise InternalException()
        result = data_string[3 : data_length]
        if result and result[0] == '?' :
            error_string = result[1 :]
            error = cls.__ERROR.get(error_string)
            if error is None :
                raise InternalException()
            error()
        return status, None, result

    @classmethod
    def __command_request_encode_basic(
        cls,
        request : str
    ) -> bytes :
        request += '\r'
        return request.encode()

    @classmethod
    def __command_request_encode_safe(
        cls,
        request : str
    ) -> bytes :
        request_bytes = request.encode()
        checksum = cls.__command_checksum_calculate(request_bytes)
        return bytes([
            cls.__STX,
            # Length (1 byte) + Checksum (2 bytes) + ETX (1 byte) = 4 bytes
            len(request_bytes) + 4,
            *request_bytes,
            *checksum.to_bytes(2, byteorder = 'big', signed = False),
            cls.__ETX
        ])

    @classmethod
    def __command_reply_receive_port_basic(cls, port : Port) -> str :
        data = port._receive(1)
        if data[0] != cls.__STX :
            raise InternalException()
        data = bytearray()
        while True :
            data_length = max(1, port._waiting_receive)
            data.extend(port._receive(data_length))
            if data[-1] == cls.__ETX :
                del data[-1]
                break
        data_string = data.decode()
        return data_string

    @classmethod
    def __command_reply_receive_port_safe(cls, port : Port) -> str :
        data_header = port._receive(2)
        if data_header[0] != cls.__STX :
            raise InternalException()
        data_length = data_header[1]
        if data_length <= 2 :
            raise InternalException()
        data = port._receive(data_length - 1)
        if data[-1] != cls.__ETX :
            raise InternalException()
        checksum = int.from_bytes(data[-3 : -1], byteorder = 'big', signed = False)
        data = data[0 : -3]
        if checksum != cls.__command_checksum_calculate(data) :
            raise ChecksumReplyException()
        data_string = data.decode()
        return data_string

    @classmethod
    def __command_transceive_port(
        cls,
        port : Port,
        safe_mode_transmit : bool,
        safe_mode_receive : bool,
        address : int,
        name : __CommandName,
        arguments : typing.Iterable[typing.Union[str, int, float]] = [],
        re_pattern_result : typing.Optional[re.Pattern] = None,
        alarm_ignore : bool = False
    ) -> typing.Tuple[Status, typing.Union[str, re.Match]] :
        while True :
            request = cls.__command_request_format(address, name, arguments)
            if safe_mode_transmit :
                request_bytes = cls.__command_request_encode_safe(request)
            else :
                request_bytes = cls.__command_request_encode_basic(request)
            port._transmit(request_bytes)
            if safe_mode_receive :
                reply = cls.__command_reply_receive_port_safe(port)
            else :
                reply = cls.__command_reply_receive_port_basic(port)
            status, alarm, result = cls.__command_reply_parse(address, reply)
            if alarm is not None and alarm_ignore :
                alarm_ignore = False
            else :
                break
        if alarm is not None :
            raise StatusAlarmException(alarm)
        if re_pattern_result is None :
            return status, result
        match = re_pattern_result.fullmatch(result)
        if match is None :
            raise InternalException()
        return status, match

    def __command_transceive(
        self,
        name : __CommandName,
        arguments : typing.Iterable[typing.Union[str, int, float]] = [],
        re_pattern_result : typing.Optional[re.Pattern] = None,
        safe_mode_transmit : typing.Optional[bool] = None,
        safe_mode_receive : typing.Optional[bool] = None,
        alarm_ignore : bool = False
    ) -> typing.Tuple[Status, typing.Union[str, re.Match]] :
        if safe_mode_transmit is None :
            safe_mode_transmit = self.__safe_mode
        if safe_mode_receive is None :
            safe_mode_receive = safe_mode_transmit
        with self.__port_lock :
            reply = Pump.__command_transceive_port(
                self.__port,
                safe_mode_transmit,
                safe_mode_receive,
                self.__address,
                name,
                arguments,
                re_pattern_result,
                alarm_ignore
            )
        if self.__heartbeat_event is not None :
            self.__heartbeat_event.set()
        return reply

    def __heartbeat_setup(self, timeout_seconds : float) -> None :
        activate = timeout_seconds != 0
        active = self.__heartbeat_thread is not None
        self.__heartbeat_event_timeout = timeout_seconds / 2
        if activate == active :
            if activate :
                self.__heartbeat_event.set()
            return
        if activate :
            self.__heartbeat_thread = threading.Thread(
                target = self.__heartbeat,
                daemon = True
            )
            self.__heartbeat_event = threading.Event()
            self.__heartbeat_thread.start()
        else :
            self.__heartbeat_event.set()
            self.__heartbeat_thread.join()
            self.__heartbeat_event = None
            self.__heartbeat_thread = None

    def __heartbeat(self) -> None :
        while self.__heartbeat_event_timeout != 0.0 :
            if self.__heartbeat_event.wait(self.__heartbeat_event_timeout) :
                self.__heartbeat_event.clear()
            else :
                self.__command_transceive(Pump.__CommandName.STATUS)