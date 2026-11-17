"""Small helpers shared by the Part A scripts (works with paho-mqtt 1.x and 2.x)."""
import os
import time
import datetime as dt
import paho.mqtt.client as mqtt

HOST = os.environ.get("MQTT_HOST", "localhost")
PORT = int(os.environ.get("MQTT_PORT", "1883"))


def make_client(client_id, **kwargs):
    """Create a paho client; paho 2.x needs an explicit callback API version."""
    if hasattr(mqtt, "CallbackAPIVersion"):
        return mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=client_id, **kwargs)
    return mqtt.Client(client_id=client_id, **kwargs)


def ts():
    """Timestamp used on every console line (HH:MM:SS.mmm)."""
    return dt.datetime.now().strftime("%H:%M:%S.%f")[:-3]


def log(tag, msg):
    print(f"{ts()} [{tag}] {msg}", flush=True)
