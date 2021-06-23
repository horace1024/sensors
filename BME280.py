# -*- coding: utf-8 -*-
from smbus2 import SMBus
import time


# Create a virtual BME280 Temp, Pressure, Humidity sensor
class BME280:
    def __init__(self, bus, addr):
        self.addr = addr
        self.bus = SMBus(bus)

        # Sample mode
        self.mode = 0x3

        # Oversampling params
        self.osrs_t = 0x5
        self.osrs_h = 0x5
        self.osrs_p = 0x5

        # Config register
        self.t_sb = 0x6
        self.filter = 0x4
        self.spi3w_en = 0x0

        # Trimming parameters
        self.dig_T1 = 0.0
        self.dig_T2 = 0.0
        self.dig_T3 = 0.0
        self.dig_P1 = 0.0
        self.dig_P2 = 0.0
        self.dig_P3 = 0.0
        self.dig_P4 = 0.0
        self.dig_P5 = 0.0
        self.dig_P6 = 0.0
        self.dig_P7 = 0.0
        self.dig_P8 = 0.0
        self.dig_P9 = 0.0
        self.dig_H1 = 0.0
        self.dig_H2 = 0.0
        self.dig_H3 = 0.0
        self.dig_H4 = 0.0
        self.dig_H5 = 0.0
        self.dig_H6 = 0.0

        # Initialise device
        self.set_ctrl_hum()
        self.set_config()
        self.set_ctrl_meas()
        self.get_trim_data()
        # self.print_trim_data()

    # Get compensated measurements
    def get_measurements(self):
        t_raw, p_raw, h_raw = self.get_raw()

        # Compute compensated temperature
        t1 = (t_raw / 16384.0 - self.dig_T1 / 1024.0) * self.dig_T2
        t2 = (t_raw / 131072.0 - self.dig_T1 / 8192.0) * (t_raw / 131072.0 - self.dig_T1 / 8192.0) * self.dig_T3
        t_fine = t1 + t2
        t_comp = t_fine / 5120.0

        # Compute compensated pressure
        p1 = (t_fine / 2.0) - 64000.0
        p2 = (((p1 / 4.0) * (p1 / 4.0)) / 2048) * self.dig_P6
        p2 += ((p1 * self.dig_P5) * 2.0)
        p2 = (p2 / 4.0) + (self.dig_P4 * 65536.0)
        p1 = (((self.dig_P3 * (((p1 / 4.0) * (p1 / 4.0)) / 8192)) / 8) + ((self.dig_P2 * p1) / 2.0)) / 262144
        p1 = ((32768 + p1) * self.dig_P1) / 32768
        # Avoid division by zero
        if p1 == 0:
            p_comp = 0.0
        else:
            pressure = ((1048576 - p_raw) - (p2 / 4096)) * 3125
            if pressure < 0x80000000:
                pressure = (pressure * 2.0) / p1
            else:
                pressure = (pressure / p1) * 2
            p1 = (self.dig_P9 * (((pressure / 8.0) * (pressure / 8.0)) / 8192.0)) / 4096
            p2 = ((pressure / 4.0) * self.dig_P8) / 8192.0
            pressure += ((p1 + p2 + self.dig_P7) / 16.0)
            p_comp = pressure / 100

        # Compute compensated humidity
        h1 = t_fine - 76800.0
        if h1 == 0:
            h_comp = 0.0
        else:
            h1 = (h_raw - (self.dig_H4 * 64.0 + self.dig_H5 / 16384.0 * h1)) * (
                    self.dig_H2 / 65536.0 * (1.0 + self.dig_H6 / 67108864.0 * h1 * (
                    1.0 + self.dig_H3 / 67108864.0 * h1)))
            h1 *= (1.0 - self.dig_H1 * h1 / 524288.0)
            # Check within bounds
            if h1 > 100.0:
                h_comp = 100.0
            elif h1 < 0.0:
                h_comp = 0.0
            else:
                h_comp = h1

        # Return all compensated as a tuple
        return "{:.2f}".format(round(t_comp, 2)), "{:.2f}".format(round(p_comp, 2)), "{:.2f}".format(round(h_comp, 2))

    # Get all T, P & H measurements
    def get_raw(self):
        # Read all at once from 0xF7 to 0xFE
        data = self.bus.read_i2c_block_data(self.addr, 0xF7, 8)
        p_raw = ((data[0] & 0xFF) << 12) + ((data[1] & 0xFF) << 4) + ((data[2] & 0xF0) >> 4)
        t_raw = ((data[3] & 0xFF) << 12) + ((data[4] & 0xFF) << 4) + ((data[5] & 0xF0) >> 4)
        h_raw = ((data[6] & 0xFF) << 8) + (data[7] & 0xFF)
        return t_raw, p_raw, h_raw

    # Perform device reset
    def reset(self):
        self.bus.write_byte_data(self.addr, 0xE0, 0xB6)
        print("BME280 0x%02X RESET" % self.addr)

    # Get ID of device
    def get_id(self):
        data = self.bus.read_byte_data(self.addr, 0xD0)
        if data != 0x60:
            print("BME280 0x%02X ID readback ERROR, read: 0x%02X" % (self.addr, data))
        return data

    # Set the CONFIG register
    def set_config(self):
        data = ((self.t_sb & 0x7) << 5) + ((self.filter & 0x7) << 2) + (self.spi3w_en & 0x1)
        self.bus.write_byte_data(self.addr, 0xF5, data)
        time.sleep(0.1)
        out = self.bus.read_byte_data(self.addr, 0xF5)
        if out != data:
            print("BME280 0x%02X Set CONFIG reg ERROR, data: 0x%02X, out: 0x%02X" % (self.addr, data, out))

    # Set the CTRL_MEAS register
    def set_ctrl_meas(self):
        data = ((self.osrs_t & 0x7) << 5) + ((self.osrs_p & 0x7) << 2) + (self.mode & 0x3)
        self.bus.write_byte_data(self.addr, 0xF4, data)
        time.sleep(0.1)
        out = self.bus.read_byte_data(self.addr, 0xF4)
        if out != data:
            print("BME280 0x%02X Set CTRL_MEAS reg ERROR, data: 0x%02X, out: 0x%02X" % (self.addr, data, out))

    # Set the CTRL_HUM register
    def set_ctrl_hum(self):
        data = self.osrs_h & 0x7
        self.bus.write_byte_data(self.addr, 0xF2, data)
        time.sleep(0.1)
        out = self.bus.read_byte_data(self.addr, 0xF2)
        if out != data:
            print("BME280 0x%02X Set CTRL_HUM reg ERROR, data: 0x%02X, out: 0x%02X" % (self.addr, data, out))

    # Get the STATUS return 0 for update, 1 for measuring
    def get_status(self):
        data = self.bus.read_byte_data(self.addr, 0xF3)
        print("BME280 0x%02X Get STATUS reg, data: 0x%02X" % (self.addr, data))
        if (data & 0x1) or (data & 0x8):
            return 1
        return 0

    # Get trimming data and store in self
    def get_trim_data(self):
        # Get all trimming bytes
        data = self.bus.read_i2c_block_data(self.addr, 0x88, 26)
        # Temperature
        self.dig_T1 = (data[0] & 0xFF) + ((data[1] & 0xFF) << 8)
        self.dig_T2 = (data[2] & 0xFF) + ((data[3] & 0xFF) << 8)
        if self.dig_T2 & 0x8000:
            self.dig_T2 = self.dig_T2 - (1 << 16)
        self.dig_T3 = (data[4] & 0xFF) + ((data[5] & 0xFF) << 8)
        if self.dig_T3 & 0x8000:
            self.dig_T3 = self.dig_T3 - (1 << 16)
        # Pressure
        self.dig_P1 = (data[6] & 0xFF) + ((data[7] & 0xFF) << 8)
        self.dig_P2 = (data[8] & 0xFF) + ((data[9] & 0xFF) << 8)
        if self.dig_P2 & 0x8000:
            self.dig_P2 = self.dig_P2 - (1 << 16)
        self.dig_P3 = (data[10] & 0xFF) + ((data[11] & 0xFF) << 8)
        if self.dig_P3 & 0x8000:
            self.dig_P3 = self.dig_P3 - (1 << 16)
        self.dig_P4 = (data[12] & 0xFF) + ((data[13] & 0xFF) << 8)
        if self.dig_P4 & 0x8000:
            self.dig_P4 = self.dig_P4 - (1 << 16)
        self.dig_P5 = (data[14] & 0xFF) + ((data[15] & 0xFF) << 8)
        if self.dig_P5 & 0x8000:
            self.dig_P5 = self.dig_P5 - (1 << 16)
        self.dig_P6 = (data[16] & 0xFF) + ((data[17] & 0xFF) << 8)
        if self.dig_P6 & 0x8000:
            self.dig_P6 = self.dig_P6 - (1 << 16)
        self.dig_P7 = (data[18] & 0xFF) + ((data[19] & 0xFF) << 8)
        if self.dig_P7 & 0x8000:
            self.dig_P7 = self.dig_P7 - (1 << 16)
        self.dig_P8 = (data[20] & 0xFF) + ((data[21] & 0xFF) << 8)
        if self.dig_P8 & 0x8000:
            self.dig_P8 = self.dig_P8 - (1 << 16)
        self.dig_P9 = (data[22] & 0xFF) + ((data[23] & 0xFF) << 8)
        if self.dig_P9 & 0x8000:
            self.dig_P9 = self.dig_P9 - (1 << 16)
        # Humidity
        self.dig_H1 = data[25] & 0xFF
        data = self.bus.read_i2c_block_data(self.addr, 0xE1, 7)
        self.dig_H2 = (data[0] & 0xFF) + ((data[1] & 0xFF) << 8)
        if self.dig_H2 & 0x8000:
            self.dig_H2 = self.dig_H2 - (1 << 16)
        self.dig_H3 = data[2] & 0xFF
        self.dig_H4 = ((data[3] & 0xFF) << 4) + (data[4] & 0x0F)
        if self.dig_H4 & 0x0800:
            self.dig_H4 = self.dig_H4 - (1 << 12)
        self.dig_H5 = ((data[4] & 0xF0) >> 4) + ((data[5] & 0xFF) << 4)
        if self.dig_H5 & 0x0800:
            self.dig_H5 = self.dig_H5 - (1 << 12)
        self.dig_H6 = data[6] & 0xFF
        if self.dig_H6 & 0x80:
            self.dig_H6 = self.dig_H6 - (1 << 8)

    # Debug print calibration data
    def print_trim_data(self):
        print("BME280 0x%02X dig_T1: %d" % (self.addr, self.dig_T1))
        print("BME280 0x%02X dig_T2: %d" % (self.addr, self.dig_T2))
        print("BME280 0x%02X dig_T3: %d" % (self.addr, self.dig_T3))
        print("BME280 0x%02X dig_P1: %d" % (self.addr, self.dig_P1))
        print("BME280 0x%02X dig_P2: %d" % (self.addr, self.dig_P2))
        print("BME280 0x%02X dig_P3: %d" % (self.addr, self.dig_P3))
        print("BME280 0x%02X dig_P4: %d" % (self.addr, self.dig_P4))
        print("BME280 0x%02X dig_P5: %d" % (self.addr, self.dig_P5))
        print("BME280 0x%02X dig_P6: %d" % (self.addr, self.dig_P6))
        print("BME280 0x%02X dig_P7: %d" % (self.addr, self.dig_P7))
        print("BME280 0x%02X dig_P8: %d" % (self.addr, self.dig_P8))
        print("BME280 0x%02X dig_P9: %d" % (self.addr, self.dig_P9))
        print("BME280 0x%02X dig_H1: %d" % (self.addr, self.dig_H1))
        print("BME280 0x%02X dig_H2: %d" % (self.addr, self.dig_H2))
        print("BME280 0x%02X dig_H3: %d" % (self.addr, self.dig_H3))
        print("BME280 0x%02X dig_H4: %d" % (self.addr, self.dig_H4))
        print("BME280 0x%02X dig_H5: %d" % (self.addr, self.dig_H5))
        print("BME280 0x%02X dig_H6: %d" % (self.addr, self.dig_H6))
