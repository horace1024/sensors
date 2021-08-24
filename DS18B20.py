# -*- coding: utf-8 -*-
from w1thermsensor import W1ThermSensor, Sensor
from w1thermsensor import W1ThermSensorError, KernelModuleLoadError, NoSensorFoundError, SensorNotReadyError, ResetValueError


# Create a virtual DS18B20 1-Wire Temperature sensor
class DS18B20:
    def __init__(self, device_id, resolution=9, cal_t=0.0):
        self.device_id = device_id
        self.resolution = resolution
        self.cal_t = cal_t
        self.sensor = None
        self.init()

    # Create the sensor and init
    def init(self):
        try:
            # Init the sensor. Note the offset could be applied here.
            self.sensor = W1ThermSensor(sensor_type=Sensor.DS18B20, sensor_id=self.device_id)
            self.sensor.set_resolution(self.resolution)
        except NoSensorFoundError as e:
            print("1-Wire temperature sensor DS18B20 with id: {0} not found".format(self.device_id), flush=True)
            raise Exception()
        except KernelModuleLoadError as e:
            print("1-Wire temperature sensor DS18B20 with id: {0} failed to load kernel module, check run as root".format(self.device_id), flush=True)
            raise Exception()

    # Read the sensor, apply calibration and return
    def t_read(self):
        try:
            temp = self.sensor.get_temperature()
        except NoSensorFoundError as e:
            print("1-Wire temperature sensor DS18B20 with id: {0} not found".format(self.device_id), flush=True)
            raise Exception()
        except SensorNotReadyError as e:
            print("1-Wire temperature sensor DS18B20 with id: {0} not ready".format(self.device_id), flush=True)
            raise Exception()
        except ResetValueError as e:
            print("1-Wire temperature sensor DS18B20 with id: {0} has reset".format(self.device_id), flush=True)
            raise Exception()
        else:
            return round((temp + self.cal_t), 2)
