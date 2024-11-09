"""GRBL Commands for GRBL Version 1.1."""

from enum import Enum


class NonGCodeCommands(Enum):
    """Non GCode commands that can be sent to the CNC mill."""

    DISPLAY_SETTINGS = "$$"
    CHANGE_SETTING = "$x=val"
    VIEW_PARAMETERS = "$#"
    VIEW_PARSER_STATE = "$G"
    TOGGLE_CHECK_MODE = "$C"
    RUN_HOMING_CYCLE = "$H"
    RUN_JOGGING_MOTION = "$J=gcode"
    KILL_ALARM_LOCK = "$X"
    VIEW_BUILD_INFO = "$I"
    VIEW_STARTUP_CODE = "$N"
    SAVE_STARTUP_CODE = "$Nx=line"
    RESTORE_SETTINGS = "$RST=$"
    ERASE_OFFSETS = "$RST=#"
    CLEAR_LOAD_DATA = "$RST=*"
    ENABLE_SLEEP_MODE = "$SLP"
    SOFT_RESET = "0x18"
    STATUS_REPORT = "?"
    CYCLE_START_RESUME = "~"
    FEED_HOLD = "!"


class GRBLSettings:
    """GRBL settings that can be changed."""

    def __init__(self):
        pass

    def step_pulse(self, argument):
        """Step pulse, microseconds"""
        return f"$0:{argument}"

    def step_idle_delay(self, argument):
        """Step idle delay, milliseconds"""
        return f"$1:{argument}"

    def step_port_invert(self, argument):
        """Step port invert, XYZmask*"""
        return f"$2:{argument}"

    def direction_port_invert(self, argument):
        """Direction port invert, XYZmask*

        The direction each axis moves."""
        return f"$3:{argument}"

    def step_enable_invert(self, argument):
        """Step enable invert, (0=Disable, 1=Invert)"""
        return f"$4:{argument}"

    def limit_pins_invert(self, argument):
        """Limit pins invert, (0=N-Open. 1=N-Close)"""
        return f"$5:{argument}"

    def probe_pin_invert(self, argument):
        """Probe pin invert, (0=N-Open. 1=N-Close)"""
        return f"$6:{argument}"

    def status_report(self, argument):
        """
        Status report
        '?' status.
        0=WCS position,
        1=report with machine position (MPos) and no buffer data reports,
        2=work position (WPos) and buffer data,
        3=plan/buffer and Machine position."""
        return f"$10:{argument}"

    def junction_deviation(self, argument):
        """Junction deviation, mm"""
        return f"$11:{argument}"

    def arc_tolerance(self, argument):
        """Arc tolerance, mm"""
        return f"$12:{argument}"

    def report_in_inches(self, argument):
        """Report in inches, (0=mm. 1=Inches)**"""
        return f"$13:{argument}"

    def soft_limits(self, argument):
        """Soft limits, (0=Disable. 1=Enable, Homing must be enabled)"""
        return f"$20:{argument}"

    def hard_limits(self, argument):
        """Hard limits, (0=Disable. 1=Enable)"""
        return f"$21:{argument}"

    def homing_cycle(self, argument):
        """Homing cycle, (0=Disable. 1=Enable)"""
        return f"$22:{argument}"

    def homing_direction_invert(self, argument):
        """Homing direction invert, XYZmask* Sets which corner it homes to."""
        return f"$23:{argument}"

    def homing_feed(self, argument):
        """Homing feed, mm/min"""
        return f"$24:{argument}"

    def homing_seek(self, argument):
        """Homing seek, mm/min"""
        return f"$25:{argument}"

    def homing_debounce(self, argument):
        """Homing debounce, milliseconds"""
        return f"$26:{argument}"

    def homing_pull_off(self, argument):
        """Homing pull-off, mm"""
        return f"$27:{argument}"

    def max_spindle_speed(self, argument):
        """Max spindle speed, RPM"""
        return f"$30:{argument}"

    def min_spindle_speed(self, argument):
        """Min spindle speed, RPM"""
        return f"$31:{argument}"

    def laser_mode(self, argument):
        """Laser mode, (0=Off, 1=On)"""
        return f"$32:{argument}"

    def x_steps_per_mm(self, argument):
        """Number of X steps to move 1mm"""
        return f"$100:{argument}"

    def y_steps_per_mm(self, argument):
        """Number of Y steps to move 1mm"""
        return f"$101:{argument}"

    def z_steps_per_mm(self, argument):
        """Number of Z steps to move 1mm"""
        return f"$102:{argument}"

    def x_max_rate(self, argument):
        """X Max rate, mm/min"""
        return f"$110:{argument}"

    def y_max_rate(self, argument):
        """Y Max rate, mm/min"""
        return f"$111:{argument}"

    def z_max_rate(self, argument):
        """Z Max rate, mm/min"""
        return f"$112:{argument}"

    def x_acceleration(self, argument):
        """X Acceleration, mm/sec^2"""
        return f"$120:{argument}"

    def y_acceleration(self, argument):
        """Y Acceleration, mm/sec^2"""
        return f"$121:{argument}"

    def z_acceleration(self, argument):
        """Z Acceleration, mm/sec^2"""
        return f"$122:{argument}"

    def x_max_travel(self, argument):
        """X Max travel, mm Only for Homing and Soft Limits."""
        return f"$130:{argument}"

    def y_max_travel(self, argument):
        """Y Max travel, mm Only for Homing and Soft Limits."""
        return f"$131:{argument}"

    def z_max_travel(self, argument):
        """Z Max travel, mm Only for Homing and Soft Limits."""
        return f"$132:{argument}"


class GRBLCodes:
    """GRBL codes for CNC milling."""

    def __init__(self):
        pass

    def set_feed_rate(self, argument):
        """Set Feed rate in Units/min (See G20/G21)."""
        return f"F{argument}"

    def rapid_positioning(self):
        """A Rapid positioning move at the Rapid Feed Rate.
        In Laser mode Laser will be turned off."""
        return "G0"

    def cutting_move(self):
        """A Cutting move in a straight line. At the Current F rate."""
        return "G1"

    def clockwise_arc(self):
        """Cut a Clockwise arc."""
        return "G2"

    def anticlockwise_arc(self):
        """Cut an Anti-Clockwise arc."""
        return "G3"

    def pause_command(self, time):
        """
        Pause command execution for the time in Pnnn. P specifies the time in seconds.
        Other systems use milliseconds as the pause time,
        if used unchanged this can result in VERY long pauses."""
        return f"G4 P{time}"

    def set_saved_origin_offset(self):
        """Sets the offset for a saved origin using absolute machine coordinates."""
        return "G10 L2"

    def set_current_position_offset(self):
        """As G10 L2 but the XYZ parameters are offsets from the current position."""
        return "G10 L20"

    def draw_arcs_xy_plane(self):
        """Draw Arcs in the XY plane, default."""
        return "G17"

    def draw_arcs_zx_plane(self):
        """Draw Arcs in the ZX plane."""
        return "G18"

    def draw_arcs_yz_plane(self):
        """Draw Arcs in the YZ plane."""
        return "G19"

    def distances_in_inches(self):
        """All distances and positions are in Inches."""
        return "G20"

    def distances_in_mm(self):
        """All distances and positions are in mm."""
        return "G21"

    def go_to_safe_position(self):
        """
        Go to safe position.
        NOTE: If you have not run a homing cycle and have set the safe position
        this is very UNSAFE to use.
        """
        return "G28"

    def set_safe_position(self):
        """Set Safe position using absolute machine coordinates."""
        return "G28.1"

    def go_to_saved_position(self):
        """Go to the saved G30 position."""
        return "G30"

    def set_predefined_position(self):
        """
        Set Predefined position using absolute machine coordinates,
        a rapid G0 move to that position will be performed before the coordinates are saved.
        """
        return "G30.1"

    def probe_towards_stock(self):
        """Probe towards the stock, error on a failure."""
        return "G38.2"

    def probe_towards_stock_no_error(self):
        """As G38.2, no error on failure."""
        return "G38.3"

    def probe_towards_stock_move_away(self):
        """As G38.2 but move away, stop on a loss of contact."""
        return "G38.4"

    def probe_towards_stock_move_away_no_error(self):
        """As G38.4, no error on failure."""
        return "G38.5"

    def cutter_compensation_off(self):
        """Cutter Compensation off. Grbl does not support cutter compensation."""
        return "G40"

    def dynamic_tool_length_offset(self):
        """Dynamic Tool length offset, offsets Z end of tool position for subsequent moves."""
        return "G43.1"

    def cancel_tool_length_offset(self):
        """Cancel Tool length Offset."""
        return "G49"

    def use_machine_coordinates(self):
        """Use machine coordinates in this command."""
        return "G53"

    def activate_saved_origin(self, index):
        """Activate the relevant saved origin."""
        return f"G54{index}"

    def exact_path_mode(self):
        """Exact Path mode. Grbl does not support any other modes."""
        return "G61"

    def canned_cycle_cancel(self):
        """
        Canned Cycle Cancel. Grbl does not support any of the canned cycle modes
        which this cancels so it does nothing.
        """
        return "G80"

    def absolute_distances(self):
        """All distances and positions are Absolute values from the current origin."""
        return "G90"

    def relative_distances(self):
        """All distances and positions are Relative values from the current position."""
        return "G91"

    def arc_incremental_position_mode(self):
        """Sets Arc incremental position mode."""
        return "G91.1"

    def set_current_coordinate_point(self):
        """
        Sets the current coordinate point, used to set an origin point of zero, commonly
        known as the home position.
        """
        return "G92"

    def reset_g92_offsets(self):
        """Reset any G92 offsets in effect to zero and zero any saved values."""
        return "G92.1"

    def inverse_time_motion_mode(self):
        """Inverse time motion mode."""
        return "G93"

    def units_per_minute_mode(self):
        """Units/min mode at the current F rate."""
        return "G94"

    def pause(self):
        """Pause."""
        return "M0"

    def optional_stop_pause(self):
        """As M0 but only pauses if an optional stop switch is on."""
        return "M1"

    def program_end(self):
        """Program End, turn off spindle/laser and stops the machine."""
        return "M2"

    def start_spindle_clockwise(self):
        """Start spindle clockwise. In Laser mode sets Constant power."""
        return "M3"

    def start_spindle_dynamic_power(self):
        """As M3, In Laser Mode sets Dynamic power."""
        return "M4"

    def stop_spindle(self):
        """Stop the Spindle."""
        return "M5"

    def coolant_on_flood(self):
        """Coolant on as a flood. (Same as M7)"""
        return "M8"

    def coolant_off(self):
        """Coolant off."""
        return "M9"

    def program_end_same_as_m2(self):
        """Same as M2."""
        return "M30"

    def set_spindle_speed(self, argument):
        """Set Spindle speed in RPM or Laser Power."""
        return f"S{argument}"
