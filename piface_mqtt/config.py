"""Configuration model for the PiFace MQTT bridge."""

from dataclasses import dataclass, field
from typing import Optional
import yaml


@dataclass
class MqttConfig:
    broker: str = "localhost"
    port: int = 1883
    username: Optional[str] = None
    password: Optional[str] = None
    topic_prefix: str = "piface"
    client_id: str = "piface-mqtt"
    keepalive: int = 60


@dataclass
class PifaceConfig:
    boards: int = 1
    poll_interval: float = 0.1


@dataclass
class HomeAssistantConfig:
    discovery: bool = True
    discovery_prefix: str = "homeassistant"


@dataclass
class BridgeConfig:
    mqtt: MqttConfig = field(default_factory=MqttConfig)
    piface: PifaceConfig = field(default_factory=PifaceConfig)
    homeassistant: HomeAssistantConfig = field(default_factory=HomeAssistantConfig)


def _parse_bool(value, setting_name: str) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "on", "yes"}:
            return True
        if normalized in {"0", "false", "off", "no"}:
            return False
    raise ValueError(
        f"{setting_name} must be a boolean or one of: true/false, on/off, yes/no, 1/0"
    )


def load_config(path: str) -> BridgeConfig:
    """Load and parse a YAML configuration file into a BridgeConfig object."""
    with open(path, "r") as fh:
        raw = yaml.safe_load(fh) or {}

    mqtt_raw = raw.get("mqtt", {})
    piface_raw = raw.get("piface", {})
    ha_raw = raw.get("homeassistant", {})

    mqtt = MqttConfig(
        broker=mqtt_raw.get("broker", "localhost"),
        port=int(mqtt_raw.get("port", 1883)),
        username=mqtt_raw.get("username") or None,
        password=mqtt_raw.get("password") or None,
        topic_prefix=mqtt_raw.get("topic_prefix", "piface"),
        client_id=mqtt_raw.get("client_id", "piface-mqtt"),
        keepalive=int(mqtt_raw.get("keepalive", 60)),
    )

    piface = PifaceConfig(
        boards=int(piface_raw.get("boards", 1)),
        poll_interval=float(piface_raw.get("poll_interval", 0.1)),
    )

    ha = HomeAssistantConfig(
        discovery=_parse_bool(ha_raw.get("discovery", True), "homeassistant.discovery"),
        discovery_prefix=ha_raw.get("discovery_prefix", "homeassistant"),
    )

    return BridgeConfig(mqtt=mqtt, piface=piface, homeassistant=ha)
