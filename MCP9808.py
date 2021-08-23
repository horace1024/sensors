# -*- coding: utf-8 -*-
from smbus2 import SMBus


# Create a virtual MCP9808 Temperature sensor
class MCP9808:
    def __init__(self, bus, addr, resolution=0x03, cal_t=0.0):
        self.addr = addr
        self.res = resolution
        self.cal_t = cal_t
        self.bus = SMBus(bus)
        self.init()

    # Initialise the MCP9808 with resolution for continuous readings
    def init(self):
        # Write config
        config = [0x00, 0x00]
        self.bus.write_i2c_block_data(self.addr, 0x01, config)
        # Write resolution
        if (self.res > 0x03) or (self.res < 0):
            self.res = 0x03
        self.bus.write_byte_data(self.addr, 0x08, self.res)
        # Read Device ID/Revision register
        rid = self.bus.read_byte_data(self.addr, 0x07)
        tmp = self.bus.read_i2c_block_data(self.addr, 0x06, 2)
        mid = ((tmp[0] & 0x1F) * 256) + tmp[1]
        # print "Init MCP9808 Manufacurer ID: 0x{:04x}, Device ID: 0x{:02x}".format(mid, rid)

    # Obtain temperature reading
    def t_read(self):
        # Obtain temp reading in binary
        tin = self.bus.read_i2c_block_data(self.addr, 0x05, 2)
        bt = ((tin[0] & 0x1F) * 256) + tin[1]
        # Check if two's comp
        if bt > 4095:
            bt -= 8192
        # Multiply by resolution
        if self.res == 0x00:
            c_temp = bt * 0.5
        elif self.res == 0x01:
            c_temp = bt * 0.25
        elif self.res == 0x02:
            c_temp = bt * 0.125
        elif self.res == 0x03:
            c_temp = bt * 0.0625
        else:
            c_temp = bt * 0.0625

        # Apply linear calibration, round and format
        return round((c_temp + self.cal_t), 2)
