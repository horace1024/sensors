# -*- coding: utf-8 -*-
from smbus2 import SMBus
import time
from datetime import datetime


# Create a virtual SHT31 Humidity and Temperature sensor
class SHT31:
    def __init__(self, bus, addr, crc=False, cal_t=0.0, cal_h=0.0):
        self.addr = addr
        self.crc = crc
        self.cal_t = cal_t
        self.cal_h = cal_h
        self.bus = SMBus(bus)
        self.init()

    # Initialise the SHT31
    def init(self):
        print("SHT31 perform CRC check: ", self.crc)
        self.reset()

    # Perform device reset
    def reset(self):
        # Send reset word
        self.bus.write_i2c_block_data(self.addr, 0x30, [0xA2])

    # Obtain reading
    def rht_read(self):
        # Send command for single shot measurement
        self.bus.write_i2c_block_data(self.addr, 0x2C, [0x06])
        # Read temp, rh and crc
        data = self.bus.read_i2c_block_data(self.addr, 0x00, 6)

        # Parse received bytes
        temp = ((data[0] & 0xFF) << 8) + (data[1] & 0xFF)
        tcrc = (data[2] & 0xFF)
        relh = ((data[3] & 0xFF) << 8) + (data[4] & 0xFF)
        hcrc = (data[5] & 0xFF)

        # Check CRC for Temp and RH
        if self.crc:
            if self.crc_check([data[0], data[1]]) != tcrc:
                print("SHT31 CRC Error - Temperature %s" % datetime.now())
            if self.crc_check([data[3], data[4]]) != hcrc:
                print("SHT31 CRC Error - Humidity %s" % datetime.now())

        # Compute real values
        tc = -45+(175*(temp/float((2**16)-1)))
        rh = 100*(relh/float((2**16)-1))
        
        # Apply linear calibration, return both values temp & humidity
        return round((tc + self.cal_t), 2), round((rh + self.cal_h), 2)

    # Enable the onboard heater
    def heater_on(self):
        self.bus.write_i2c_block_data(self.addr, 0x30, [0x6D])

    # Disable the onboard heater
    def heater_off(self):
        self.bus.write_i2c_block_data(self.addr, 0x30, [0x66])

    # Print status register
    def print_status(self):
        # Read register
        self.bus.write_i2c_block_data(self.addr, 0xF3, [0x2D])
        data = self.bus.read_i2c_block_data(self.addr, 0x00, 3)

        # Digest
        status = ((data[0] & 0xFF) << 8) + (data[1] & 0xFF)
        scrc = (data[2] & 0xFF)

        # Check CRC
        if self.crc:
            if self.crc_check([data[0], data[1]]) != scrc:
                print("SHT31 CRC Error - Status check %s" % datetime.now())

        # Parse
        alert_pending  = ((status & 0x8000) >> 15)
        heater         = ((status & 0x2000) >> 13)
        rh_tracking    = ((status & 0x0800) >> 11)
        t_tracking     = ((status & 0x0400) >> 10)
        sys_reset      = ((status & 0x0010) >> 4)
        command_status = ((status & 0x0002) >> 1)
        write_checksum = ((status & 0x0001) >> 0)

        # Print
        print("Alert pending status       : 0x%01X" % alert_pending)
        print("Heater status              : 0x%01X" % heater)
        print("TRH tracking alert         : 0x%01X" % rh_tracking)
        print("T tracking alert           : 0x%01X" % t_tracking)
        print("System reset detected      : 0x%01X" % sys_reset)
        print("Command status             : 0x%01X" % command_status)
        print("Write data checksum status : 0x%01X" % write_checksum)

    # Compute the CRC for two byte data
    def crc_check(self, data):
        crc = 0xFF
        for byte in data:
            crc ^= byte
            for _ in range(8):
                if crc & 0x80:
                    crc <<= 1
                    crc ^= 0x131
                else:
                    crc <<= 1
        return crc
