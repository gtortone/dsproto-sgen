#!/usr/bin/env python3

import sys
import midas
import midas.frontend
import midas.event
from pyvisa import ResourceManager, constants

from sgendriver import SGENModel, SGENDevice, SGENFactory
from utils import flatten_dict

class SGEN(midas.frontend.EquipmentBase):

    def __init__(self, client, session, model):

        self.session = session
        self.sgen = SGENFactory(model, session)

        equip_name = f'SGEN-{model}-{str(midas.frontend.frontend_index).zfill(2)}'

        default_common = midas.frontend.InitialEquipmentCommon()
        default_common.equip_type = midas.EQ_PERIODIC
        default_common.buffer_name = "SYSTEM"
        default_common.trigger_mask = 0
        default_common.event_id = 85
        default_common.period_ms = 5000   # event data frequency update (in milliseconds)
        default_common.read_when = midas.RO_ALWAYS
        default_common.log_history = 1

        midas.frontend.EquipmentBase.__init__(self, client, equip_name, default_common, self.sgen.getSettingsSchema());

        self.odb_readback_dir = f"/Equipment/{equip_name}/Readback"

        self.updateODB()

    def debug(self):
        self.sgen.debug()

    def readout_func(self):
        self.updateODB()
        #self.debug()

        event = midas.event.Event()

        func = self.sgen.getShape()

        data = []
        data.append(float(self.sgen.getFrequency()))
        data.append(float(self.sgen.getVoltageHigh()))
        data.append(float(self.sgen.getVoltageLow()))
        data.append(float(self.sgen.getOutput()))

        if func == "PULS":
            data.append(float(self.sgen.getPulseWidth()))
        
        event.create_bank("FUNC", midas.TID_INT32, [self.sgen.getShapeIndex()])
        event.create_bank("PARA", midas.TID_FLOAT, data)

        return event

    def detailed_settings_changed_func(self, path, idx, new_value):
        if path == f'{self.odb_settings_dir}/output':
            self.sgen.setOutput(new_value)
        elif path == f'{self.odb_settings_dir}/shape':
            self.sgen.setShape(new_value)
        elif path == f'{self.odb_settings_dir}/frequency':
            self.sgen.setFrequency(new_value)
        elif path == f'{self.odb_settings_dir}/Vhigh':
            self.sgen.setVoltageHigh(new_value)
        elif path == f'{self.odb_settings_dir}/Vlow':
            self.sgen.setVoltageLow(new_value)
        elif path == f'{self.odb_settings_dir}/pulse/width':
            self.sgen.setPulseWidth(new_value)

        error = self.sgen.getLastError()
        if error[0] != 0:
            self.client.msg(error[1], is_error=True)

    def updateODB(self):
        readback = self.sgen.getReadbackSchema()
        settings = self.sgen.getSettingsSchema()

        settings['shape'] = self.sgen.getShape()
        readback['output'] = settings['output'] = self.sgen.getOutput()
        readback['frequency'] = settings['frequency'] = self.sgen.getFrequency()
        readback['Vhigh'] = settings['Vhigh'] = self.sgen.getVoltageHigh()
        readback['Vlow'] = settings['Vlow'] = self.sgen.getVoltageLow()
        readback['pulse']['width'] = settings['pulse']['width'] = self.sgen.getPulseWidth()

        self.client.odb_set(self.odb_readback_dir, readback, remove_unspecified_keys=False)

        if(settings != self.settings):
            local_settings = flatten_dict(settings)
            odb_settings = flatten_dict(self.settings)
            for k,v in local_settings.items():
                if local_settings[k] != odb_settings[k]:
                    self.client.odb_set(f'{self.odb_settings_dir}/{k}', v, remove_unspecified_keys=False)

class SGENFrontend(midas.frontend.FrontendBase):

    def __init__(self, session, model):
        if(midas.frontend.frontend_index == -1):
            print("set frontend index with -i option")
            sys.exit(-1)
        midas.frontend.FrontendBase.__init__(self, f"SGEN-{model}")
        self.add_equipment(SGEN(self.client, session, model))

if __name__ == "__main__":
    parser = midas.frontend.parser
    parser.add_argument("--port", default="/dev/ttyUSB0")
    parser.add_argument("--model", required=True, choices = [m.value[0] for m in SGENModel])
    args = midas.frontend.parse_args()

    # lookup for PSU on USB port
    rm = ResourceManager()
    dev = f'ASRL{args.port}::INSTR'
    session = rm.open_resource(dev, baud_rate = 9600, data_bits = 7, parity = constants.Parity.even,
                flow_control = constants.VI_ASRL_FLOW_NONE, stop_bits = constants.StopBits.two)
    session.read_termination = '\n'
    session.write_termination = '\n'

    try:
        model = session.query('*IDN?').split(',')[1]
    except Exception as e:
        print(f"E: {e}")
        sys.exit(-1)

    if model == args.model:
        print(f"I: SGEN {model} found on {args.port}")
    else:
        print(f"E: SGEN {args.model} not found on {args.port}")
        sys.exit(-1)

    equip_name = f'SGEN-{model}-{str(midas.frontend.frontend_index).zfill(2)}'

    # check if a SGEN frontend is running with same model and id
    with midas.client.MidasClient("sgen") as c:

        if c.odb_exists(f"/Equipment/{equip_name}/Common/Frontend name"):
            fename = c.odb_get(f"/Equipment/{equip_name}/Common/Frontend name")

            if c.odb_get(f"/Equipment/{equip_name}"):
                for cid in c.odb_get(f'/System/Clients'):
                    if c.odb_get(f'/System/Clients/{cid}/Name') == fename:
                        c.msg(f"{equip_name} already running on MIDAS server, please change frontend index")
                        sys.exit(-1)

    fe = SGENFrontend(session, model)
    fe.run()
