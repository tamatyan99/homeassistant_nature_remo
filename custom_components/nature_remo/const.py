DOMAIN = "nature_remo"
CONF_LOCAL_IP = "local_ip"
DEFAULT_UPDATE_INTERVAL = 60
DEFAULT_MOTION_THRESHOLD_MINUTES = 5

ON_COMMANDS = ["on", "オン", "power on", "power-on", "power_on"]
OFF_COMMANDS = ["off", "オフ", "power off", "power-off", "power_off"]

# Home Assistant HVAC mode string to Nature Remo mode
HA_MODE_TO_REMO_MODE = {
    "cool": "cool",
    "heat": "warm",
    "dry": "dry",
    "fan_only": "blow",
    "auto": "auto",
}

REMO_MODE_TO_HA_MODE = {v: k for k, v in HA_MODE_TO_REMO_MODE.items()}

# Smart Meter EPC constants
SMART_METER_EPC_COEFFICIENT = 211
SMART_METER_EPC_UNIT = 225
SMART_METER_EPC_BUY_POWER = 224
SMART_METER_EPC_SOLD_POWER = 227
SMART_METER_EPC_INSTANT_POWER = 231
