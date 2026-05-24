"""Home Assistant MQTT Discovery payload generation."""

import json
from typing import List, Tuple

from .config import BridgeConfig


def _device_info(board: int) -> dict:
    return {
        "identifiers": [f"piface_board_{board}"],
        "name": f"PiFace Digital Board {board}",
        "model": "PiFace Digital 2",
        "manufacturer": "PiFace",
    }


def build_discovery_messages(cfg: BridgeConfig) -> List[Tuple[str, str]]:
    """Return a list of (topic, payload_json) tuples for all HA discovery messages."""
    prefix = cfg.homeassistant.discovery_prefix
    topic_prefix = cfg.mqtt.topic_prefix
    messages = []

    for board in range(cfg.piface.boards):
        device = _device_info(board)

        # --- Inputs → binary_sensor ---
        for pin in range(8):
            uid = f"piface_{board}_input_{pin}"
            config_topic = f"{prefix}/binary_sensor/{uid}/config"
            payload = {
                "name": f"PiFace Board{board} Input {pin}",
                "state_topic": f"{topic_prefix}/{board}/input/{pin}/state",
                "payload_on": "1",
                "payload_off": "0",
                "unique_id": uid,
                "device": device,
            }
            messages.append((config_topic, json.dumps(payload)))

        # --- Outputs → switch ---
        for pin in range(8):
            uid = f"piface_{board}_output_{pin}"
            config_topic = f"{prefix}/switch/{uid}/config"
            payload = {
                "name": f"PiFace Board{board} Output {pin}",
                "state_topic": f"{topic_prefix}/{board}/output/{pin}/state",
                "command_topic": f"{topic_prefix}/{board}/output/{pin}/set",
                "payload_on": "1",
                "payload_off": "0",
                "unique_id": uid,
                "device": device,
            }
            messages.append((config_topic, json.dumps(payload)))

        # --- Relays (output 0 & 1) → switch ---
        for relay in range(2):
            uid = f"piface_{board}_relay_{relay}"
            config_topic = f"{prefix}/switch/{uid}/config"
            payload = {
                "name": f"PiFace Board{board} Relay {relay}",
                "state_topic": f"{topic_prefix}/{board}/relay/{relay}/state",
                "command_topic": f"{topic_prefix}/{board}/relay/{relay}/set",
                "payload_on": "1",
                "payload_off": "0",
                "unique_id": uid,
                "device": device,
            }
            messages.append((config_topic, json.dumps(payload)))

        # --- LEDs (output 0–7) → light ---
        for led in range(8):
            uid = f"piface_{board}_led_{led}"
            config_topic = f"{prefix}/light/{uid}/config"
            payload = {
                "name": f"PiFace Board{board} LED {led}",
                "state_topic": f"{topic_prefix}/{board}/led/{led}/state",
                "command_topic": f"{topic_prefix}/{board}/led/{led}/set",
                "payload_on": "1",
                "payload_off": "0",
                "unique_id": uid,
                "device": device,
            }
            messages.append((config_topic, json.dumps(payload)))

    return messages
