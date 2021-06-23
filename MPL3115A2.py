# -*- coding: utf-8 -*-
from smbus2 import SMBus
import time


# Create a virtual MPL3115A2 Pressure sensor
class MPL3115A2:
    def __init__(self, bus, addr, alt):
        self.addr = addr
        self.alt = alt
        self.bus = SMBus(bus)
        self.init()

    # Initialise the MPL3115A2
    def init(self):
        self.reset()    
        self.w_pt_data_cfg(drem=1, pdefe=0, tdefe=0)
        self.w_ctrl_reg1(alt=self.alt, os=1, sbyb=1)
        self.r_ctrl_reg1()
        self.r_ctrl_reg2()


    # Reset device
    def reset(self):
        # Reset by writing to CTRL2
        try:
            self.bus.write_byte_data(self.addr, 0x26, 0x04)
        except:
            print("MPL3115A2 SMBus reset on device reset, please wait...")
        
        time.sleep(1)
        self.r_ctrl_reg1()
        self.r_ctrl_reg2()

    # Write data config register
    def w_pt_data_cfg(self, drem=0, pdefe=0, tdefe=0):
        # Parse
        data = ((drem & 0x1) << 2) + ((pdefe & 0x1) << 1) + ((tdefe & 0x1) << 0)
        # Debug
        print("MPL3115A2 PT_DATA_CFG: 0x%02X" % data)
        # Write to device
        self.bus.write_byte_data(self.addr, 0x13, data)

    # Write control register 1
    def w_ctrl_reg1(self, alt=0, os=0, ost=0, sbyb=0):
        # Parse
        data = ((alt & 0x1) << 7) + ((os & 0x7) << 3) + ((ost & 0x1) << 1) + ((sbyb & 0x1) << 0)
        # Debug
        print("MPL3115A2 CTRL1: 0x%02X" % data)
        # Write to device
        self.bus.write_byte_data(self.addr, 0x26, data)

    # Write control register 2
    def w_ctrl_reg2(self, load=0, alarm=0, st=0):
        # Parse
        data = ((load & 0x1) << 5) + ((alarm & 0x1) << 4) + ((st & 0xF) << 0)
        # Debug
        print("MPL3115A2 CTRL2: 0x%02X" % data)
        # Write to device
        self.bus.write_byte_data(self.addr, 0x27, data)

    
    # Read pressure from device
    def p_read(self):
        # Read data from device
        data = self.bus.read_i2c_block_data(self.addr, 0x01, 3)
        # Is alt mode or pressure
        if(self.alt):
            print("MPL3115A2 Compute altitude")
            # Parse
            aint = ((data[0] & 0x7F) << 8) + ((data[1] & 0xFF) << 0)
            sign = (data[0] & 0x80)
            afrc = ((data[2] & 0xF0) >>4)
            alt = 0.0
            if(sign):
                alt -= 2**16
            alt += aint
            alt += (afrc * 0.0625)
            print("MPL3115A2 Altitude: %.4f" % alt)
            # Return
            return "{:.2f}".format(round(alt, 2))

        else:
            print("MPL3115A2 Compute pressure")
            # Parse
            pint = ((data[0] & 0xFF) << 10) + ((data[1] & 0xFF) << 2) + ((data[2] & 0xC0) >> 6)
            pfrc = ((data[2] & 0x30) >> 4)
            p = pint + (pfrc * 0.25)
            hPa = p/100
            print("MPL3115A2 Pressure: %.2f" % p)
            # Return
            return "{:.2f}".format(round(hPa, 2))

    # Read temperature data
    def t_read(self):
        self.r_ctrl_reg1()
        self.r_ctrl_reg2()
        self.r_dr_status()
        # Read data from device
        data = self.bus.read_i2c_block_data(self.addr, 0x04, 2)
        # Parse
        temp = 0.0
        tint = ((data[0] & 0x7F) << 0)
        tfrc = ((data[1] & 0xF0) >> 4)
        sign = (data[0] & 0x80)
        # Compute
        if(sign):
            temp -= 128
        temp += tint
        temp += (tfrc * 0.0625)
        print("MPL3115A2 Temp: %.4f" % temp)
        # Return
        return "{:.2f}".format(round(temp, 2))
    
    # Read data config register
    def r_pt_data_cfg(self):
        # Read byte from device
        data = self.bus.read_byte_data(self.addr, 0x13)
        # Parse
        drem  = ((data & 0x04) >> 2)
        pdefe = ((data & 0x02) >> 1)
        tdefe = ((data & 0x01) >> 0)
        # Debug
        print("MPL3115A2 DREM: 0x%02X, PDEFE: 0x%02X, TDEFE: 0x%02X" % (drem, pdefe, tdefe))
        # Return
        return drem, pdefe, tdefe

    # Read sensor status register
    def r_dr_status(self):
        # Read byte from device
        data = self.bus.read_byte_data(self.addr, 0x07)
        # Parse
        ptow = ((data & 0x80) >> 7)
        poww = ((data & 0x40) >> 6)
        tow  = ((data & 0x20) >> 5)
        ptdr = ((data & 0x08) >> 3)
        pdr  = ((data & 0x04) >> 2)
        tdr  = ((data & 0x02) >> 1)
        # Debug
        print("MPL3115A2 PTOW: 0x%02X, POW: 0x%02X, TOW: 0x%02X, PTDR: 0x%02X, PDR: 0x%02X, TDR: 0x%02X" % (ptow, poww, tow, ptdr, pdr, tdr))
        # Return
        return ptow, poww, tow, ptdr, pdr, tdr

    # Read control register 1
    def r_ctrl_reg1(self):
        # Read byte from device
        data = self.bus.read_byte_data(self.addr, 0x26)
        # Parse
        alt  = ((data & 0x80) >> 7)
        os   = ((data & 0x38) >> 3)
        rst  = ((data & 0x04) >> 2)
        ost  = ((data & 0x02) >> 1)
        sbyb = ((data & 0x01) >> 0)
        # Debug
        print("MPL3115A2 ALT: 0x%02X, OS: 0x%02X, RST: 0x%02X, OST: 0x%02X, SBYB: 0x%02X" % (alt, os, rst, ost, sbyb))
        # Return
        return alt, os, rst, ost, sbyb

    # Read control register 2
    def r_ctrl_reg2(self):
        # Read byte from device
        data = self.bus.read_byte_data(self.addr, 0x27)
        # Parse
        load  = ((data & 0x20) >> 5)
        alarm = ((data & 0x10) >> 4)
        st    = ((data & 0x0F) >> 0)
        # Debug
        print("MPL3115A2 LOAD: 0x%02X, ALARM: 0x%02X, ST: 0x%02X" % (load, alarm, st))
        # Return
        return load, alarm, st

