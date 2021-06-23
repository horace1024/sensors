# -*- coding: utf-8 -*-
from smbus2 import SMBus
from datetime import datetime, timedelta

"""
This class creates an interface to the INA233 Power Meter

Page 17 of the INA233 datasheet details the need for shifting the
value of m to reduce rounding errors. This is only necessary for 
computation on a microprocessor where floating point arithmetic is
not readily available. For this Python class, the value of m is 
never directly calculated since X=(1/m)*(Yx10^(-R)-b) and m=1/Current_LSB
therefore X=Current_LSB*Y. No m or exponent R is required. (b is always 0).

The value of Current_LSB is stored as a float and used in later
computations as such.

Check the INA233 Datasheet for details on parameters contained within
the MFR_DEVICE_CONFIG and MFR_ADC_CONFIG registers.
"""


# Create a virtual INA233 Power Meter
class INA233:
    def __init__(self, bus, addr, max_i=15.0, r_shunt=0.002, debug=False):
        self.addr = addr
        self.max_i = max_i
        self.r_shunt = r_shunt
        self.debug = debug
        self.energy_acc = 0
        self.last = datetime.utcnow()
        self.bus = SMBus(bus)
        self.init()

    # Set the INA233 to default settings
    def set_defaults(self):
        self.bus.write_byte(self.addr, 0x12)
        self.energy_acc = 0
        self.last = datetime.utcnow()

    # Initialise the INA233 for I and P readings
    def init(self):
        # Reset device to defaults
        self.set_defaults()
        
        # Debug
        if self.debug:
            print("INA233 0x%02X Init with max_i: %.1f Amps, r_shunt: %.5f ohms" % (self.addr, self.max_i, self.r_shunt))
        
        # Current LSB is stored as float so we do not need to compute m later
        self.current_lsb = float(self.max_i) / 2**15
        cal = 0.00512/(self.current_lsb * self.r_shunt)
        
        # Round to nearest int for programming
        cal_r = int(round(cal))
        
        # Debug
        if self.debug:
            print("INA233 0x%02X MFR_CALIBRATION Rounded from %.4f to %d (0x%04X)" % (self.addr, cal, cal_r, cal_r))
            print("INA233 0x%02X current_lsb: %.15f" % (self.addr, self.current_lsb))
        
        # Set calibration registers in device
        self.set_mfr_calibration(cal_r)
        self.set_mfr_device_config(read_ein=1)
        self.set_mfr_adc_config(avg=5, vbusct=5, vshct=4, mode=7)

    # Set the MFR_CALIBRATION register
    def set_mfr_calibration(self, cal):
        # Build config value
        cali = (cal & 0x7FFF)

        #Write to register
        self.bus.write_word_data(self.addr, 0xD4, cali)
        mfr_calibration = self.bus.read_word_data(self.addr, 0xD4)
        
        # Debug
        if self.debug:
            if(mfr_calibration != cali):
                print("INA233 0x%02X MFR_CALIBRATION readback error, write: 0x%04X, read: 0x%04X" % (self.addr, cali, mfr_calibration))
            else:
                print("INA233 0x%02X MFR_CALIBRATION readback OK, read: 0x%04X" % (self.addr, mfr_calibration))

    # Set MFR_ADC_CONFIG register
    def set_mfr_adc_config(self, avg=0, vbusct=4, vshct=4, mode=7):
        # Build config value
        adc_conf  = ((0x4    & 0xF) << 12)
        adc_conf += ((avg    & 0x7) << 9)
        adc_conf += ((vbusct & 0x7) << 6)
        adc_conf += ((vshct  & 0x7) << 3)
        adc_conf += ((mode   & 0x7) << 0)

        # Write to register
        self.bus.write_word_data(self.addr, 0xD0, adc_conf)
        adc_config = self.bus.read_word_data(self.addr, 0xD0)
       
        # Debug
        if self.debug:
            if(adc_config != adc_conf):
                print("INA233 0x%02X MFR_ADC_CONFIG readback error, write: 0x%04X, read: 0x%04X" % (self.addr, adc_conf, adc_config))
            else:
                print("INA233 0x%02X MFR_ADC_CONFIG readback OK, read: 0x%04X" % (self.addr, adc_config))

    #Set MFR_DEVICE_CONFIG register
    def set_mfr_device_config(self, ein_status=0, ein_accum=0, i2c_filt=0, read_ein=0, alert=1, apol=0):
        # Build config value
        dev_conf  = ((ein_status & 0x01) << 7)
        dev_conf += ((ein_accum  & 0x03) << 4)
        dev_conf += ((i2c_filt   & 0x01) << 3)
        dev_conf += ((read_ein   & 0x01) << 2)
        dev_conf += ((alert      & 0x01) << 1)
        dev_conf += ((apol       & 0x01) << 0)

        # Write to register
        self.bus.write_byte_data(self.addr, 0xD5, dev_conf)
        device_config = self.bus.read_byte_data(self.addr, 0xD5)
        
        # Debug
        if self.debug:
            if(device_config != dev_conf):
                print("INA233 0x%02X MFR_DEVICE_CONFIG readback error, write: 0x%02X, read: 0x%02X" % (self.addr, dev_conf, device_config))
            else:
                print("INA233 0x%02X MFR_DEVICE_CONFIG readback OK, read: 0x%02X" % (self.addr, device_config))

    # Obtain voltage reading
    def v_read(self):
        vin_read = float(self.bus.read_word_data(self.addr, 0x88))
        vin = (1.0/8)*(vin_read*10**-2)
        
        # Debug
        if self.debug:
            print("INA233 0x%02X Voltage : %.2fV" % (self.addr, vin))
        
        return vin

    # Obtain current reading
    def i_read(self):
        iin_read = self.bus.read_word_data(self.addr, 0x89)
        
        # Check sign
        if(iin_read & 0x8000):
            iin_read = iin_read-0x10000
        iin = self.current_lsb*iin_read
        
        # Debug
        if self.debug:
            print("INA233 0x%02X Current : %.2fA" % (self.addr, iin))
        
        return iin

    # Obtain power reading
    def p_read(self):
        pin_read = float(self.bus.read_word_data(self.addr, 0x97))
        pin = self.current_lsb*25*pin_read
        
        # Debug
        if self.debug:
            print("INA233 0x%02X Power   : %.2fW" % (self.addr, pin))
        
        return pin

    # Read total energy (kWh) since last reset
    def e_read(self):
        # Read energy register
        ein_read = self.bus.read_i2c_block_data(self.addr, 0x86, 7)
        # Get time of this read
        t = datetime.utcnow()

        # Extract sub-values
        pow_acc = (ein_read[1] & 0xFF) + ((ein_read[2] & 0xFF) << 8)
        pow_acc_roll = ein_read[3] & 0xFF
        samples = (ein_read[4] & 0xFF) + ((ein_read[5] & 0xFF) << 8) + ((ein_read[6] & 0xFF) << 16)
        
        # Total energy for this sample period (since self.last)
        # Assumes autoclear enabled in MFR_DEVICE_CONFIG
        # Assumes this command is run frequently enough to avoid roll overs (via reset on read)
        total_e = self.current_lsb*25*((pow_acc_roll * 0xFFFF) + pow_acc)

        # Energy is total power accumulated * time since measurement start
        if(samples != 0):
            dur = (t - self.last).total_seconds()
            self.last = t
            self.energy_acc += ((float(total_e)/samples)*dur)/(3600*1000)
            
            #Debug
            if self.debug:
                print("INA233 0x%02X Energy  : %.8fkWh" % (self.addr, self.energy_acc))
            
            return self.energy_acc
        else:
            return 0.0



    # Print debug information for this INA233 device
    def print_debug(self):
        print("\nDebug information for INA233 addr: 0x%02X" % self.addr)
        # Get MFR_MODEL
        mfr_model = self.bus.read_i2c_block_data(self.addr, 0x9A, 7)
        print("MFR_MODEL   : "+bytearray(mfr_model).decode('utf-8'))
        # Get MFR_ID
        mfr_id = self.bus.read_i2c_block_data(self.addr, 0x99, 3)
        print("MFR_ID      : "+bytearray(mfr_id).decode('utf-8'))
        # Get MFR_MODEL
        mfr_revision = self.bus.read_word_data(self.addr, 0x9B)
        print("MFR_REVISION: 0x%04X" % mfr_revision)
        # Get MFR_CALIBRATION
        mfr_calibration = self.bus.read_word_data(self.addr, 0xD4)
        print("MFR_CALIC   : 0x%04X" % mfr_calibration)
        # Get MFR_DEVICE_CONDIG
        mfr_dev_config = self.bus.read_byte_data(self.addr, 0xD5)
        print("MFR_DEV_CONF: 0x%02X" % mfr_dev_config)

        # Capability
        capability = self.bus.read_byte_data(self.addr, 0x19)
        print("Capability  : 0x%02X" % capability)
        # Status byte
        status_byte = self.bus.read_byte_data(self.addr, 0x78)
        print("Status byte : 0x%02X" % status_byte)
        # Status word
        status_word = self.bus.read_word_data(self.addr, 0x79)
        print("Status word : 0x%04X" % status_word)
        # Status iout
        status_iout = self.bus.read_byte_data(self.addr, 0x7B)
        print("Status IOUT : 0x%02X" % status_iout)
        # Status input
        status_input = self.bus.read_byte_data(self.addr, 0x7C)
        print("Status INPUT: 0x%02X" % status_input)
        # Status communications
        status_cml = self.bus.read_byte_data(self.addr, 0x7E)
        print("Status CML  : 0x%02X" % status_cml)
        # Status MFR Specific
        status_mfr = self.bus.read_byte_data(self.addr, 0x80)
        print("Status MFR  : 0x%02X" % status_mfr)
        # ADC_CONFIG
        adc_config = self.bus.read_word_data(self.addr, 0xD0)
        print("ADC_CONFIG  : 0x%04X" % adc_config)

        print("\n")
