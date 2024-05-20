from enum import Enum

class SGENDevice:
    def __init__(self):
        self.session = None

    def query(self, cmd):
        res = ""
        #print(f'Q: {cmd}')
        try:
            res = self.session.query(cmd)
        except Exception as e:
            print(f'E: {e}')

        return res

    def write(self, cmd):
        #print(f'W: {cmd}')
        try:
            self.session.write(cmd)
        except Exception as e:
            print(f'E: {e}')

    def reset(self):
        self.write("*RST")
        self.write("*CLS")

    def setSession(self, session):
        self.session = session

class SGENModel(Enum):
    A33250A = '33250A',

class SGENAgilent33250A(SGENDevice):
    def __init__(self):
        super().__init__()

        self.model = SGENModel.A33250A
        self.modelname = '33250A'
        self.brand = 'Agilent'
        self.shapelist = [ "SIN", "SQU", "RAMP", "PULS", "NOIS", "DC", "USER" ]

        self.settings = {
            "port" : "",
            "brand" : self.brand,
            "model" : self.modelname,
            "output" : False,
            "shape" : "",
            "frequency" : 0.0,
            "Vhigh" : 0.0,
            "Vlow" : 0.0,
            "pulse" : {
                "width" : 0.0,
            }
        }

        self.readback = {
            "output" : False,
            "frequency" : 0.0,
            "Vhigh" : 0.0,
            "Vlow" : 0.0,
            "pulse" : {
                "width" : 0.0,
            }
        }

    def getSettingsSchema(self):
        return self.settings

    def getReadbackSchema(self):
        return self.readback

    def debug(self):
        print(f'{self.brand} {self.modelname}')
        print(f'shape: {self.getShape()}')
        print(f'frequency: {float(self.getFrequency())}')
        print(f'Vhigh: {float(self.getVoltageHigh())}')
        print(f'Vlow: {float(self.getVoltageLow())}')
        print(f'pulse width: {float(self.getPulseWidth())}')
        print(f'output: {self.getOutput()}')

    def setShape(self, value):
        if value in self.shapelist:
            self.write(f"FUNC {value}")

    def getShape(self):
        return self.query("FUNC?")

    def getShapeIndex(self):
        return self.shapelist.index(self.getShape())

    def setFrequency(self, value):
        self.write(f"FREQ {value}")

    def getFrequency(self):
        return self.query("FREQ?")
        
    def setVoltageHigh(self, value):
        self.write(f"VOLT:HIGH {value}")

    def getVoltageHigh(self):
        return self.query("VOLT:HIGH?")

    def setVoltageLow(self, value):
        self.write(f"VOLT:LOW {value}")

    def getVoltageLow(self):
        return self.query("VOLT:LOW?")

    def setPulseWidth(self, value):
        self.write(f"PULSE:WIDTH {value}")

    def getPulseWidth(self):
        return self.query("PULSE:WIDTH?")

    def setOutput(self, value):
        if value in ['ON', 'OFF'] or value in [0, 1]:
            self.write(f':OUTP {value}')

    def getOutput(self):
        return int(self.query(":OUTP?"))

    def getLastError(self):
        line = self.query(":SYST:ERR?")
        errorCode = line.split(',')[0]
        return (int(errorCode), line)

def SGENFactory(model):
    if model not in [m.value[0] for m in SGENModel]:
        raise TypeError
    if model == '33250A':
        return SGENAgilent33250A()
