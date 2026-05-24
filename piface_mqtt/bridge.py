"""Main PiFace ↔ MQTT bridge logic."""

import logging
import signal
import threading
import time
from typing import Dict, List

import paho.mqtt.client as mqtt
import pifacedigitalio

from .config import BridgeConfig
from .discovery import build_discovery_messages

logger = logging.getLogger(__name__)


class PifaceMqttBridge:
    """Bridges all PiFace Digital I/Os to an MQTT broker.

    Inputs are published when they change (interrupt-driven).
    Outputs are controlled by subscribing to command topics.
    Home Assistant MQTT Discovery is published on connect.
    """

    def __init__(self, cfg: BridgeConfig):
        self._cfg = cfg
        self._boards: Dict[int, pifacedigitalio.PiFaceDigital] = {}
        self._listeners: List[pifacedigitalio.InputEventListener] = []
        self._client = mqtt.Client(client_id=cfg.mqtt.client_id)
        self._stop_event = threading.Event()

        # Last known input state per board to avoid duplicate publishes
        self._input_state: Dict[int, List[int]] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def start(self):
        """Initialise hardware, connect to MQTT and start the bridge."""
        self._init_piface()
        self._init_mqtt()
        self._publish_online()
        if self._cfg.homeassistant.discovery:
            self._publish_discovery()
        self._publish_initial_states()
        self._start_listeners()
        logger.info("PiFace MQTT bridge running. Press Ctrl+C to stop.")
        try:
            while not self._stop_event.is_set():
                time.sleep(0.5)
        finally:
            self.stop()

    def stop(self):
        """Gracefully shut down the bridge."""
        logger.info("Shutting down PiFace MQTT bridge…")
        for listener in self._listeners:
            try:
                listener.deactivate()
            except Exception:
                pass
        for board in self._boards.values():
            try:
                board.deinit_board()
            except Exception:
                pass
        self._publish_offline()
        self._client.loop_stop()
        self._client.disconnect()
        logger.info("Shutdown complete.")

    # ------------------------------------------------------------------
    # Hardware initialisation
    # ------------------------------------------------------------------

    def _init_piface(self):
        num_boards = self._cfg.piface.boards
        logger.info("Initialising %d PiFace board(s)…", num_boards)
        for addr in range(num_boards):
            board = pifacedigitalio.PiFaceDigital(hardware_addr=addr)
            self._boards[addr] = board
            self._input_state[addr] = [
                board.input_pins[pin].value for pin in range(8)
            ]
            logger.debug("Board %d initialised.", addr)

    # ------------------------------------------------------------------
    # MQTT initialisation
    # ------------------------------------------------------------------

    def _init_mqtt(self):
        cfg = self._cfg.mqtt
        if cfg.username:
            self._client.username_pw_set(cfg.username, cfg.password)

        status_topic = f"{cfg.topic_prefix}/status"
        self._client.will_set(status_topic, "offline", retain=True)

        self._client.on_connect = self._on_connect
        self._client.on_message = self._on_message

        logger.info("Connecting to MQTT broker %s:%d…", cfg.broker, cfg.port)
        self._client.connect(cfg.broker, cfg.port, cfg.keepalive)
        self._client.loop_start()

    def _on_connect(self, client, userdata, flags, rc):
        if rc != 0:
            logger.error("MQTT connection failed with code %d", rc)
            return
        logger.info("Connected to MQTT broker.")
        prefix = self._cfg.mqtt.topic_prefix
        # Subscribe to all output command topics
        for board in self._boards:
            client.subscribe(f"{prefix}/{board}/output/+/set")
            client.subscribe(f"{prefix}/{board}/relay/+/set")
            client.subscribe(f"{prefix}/{board}/led/+/set")
        logger.debug("Subscribed to output command topics.")

    def _on_message(self, client, userdata, msg):
        topic = msg.topic
        payload = msg.payload.decode().strip()
        prefix = self._cfg.mqtt.topic_prefix
        logger.debug("Received MQTT message: %s = %s", topic, payload)

        # Expected topic shapes:
        #   {prefix}/{board}/output/{pin}/set
        #   {prefix}/{board}/relay/{relay}/set
        #   {prefix}/{board}/led/{led}/set
        parts = topic.split("/")
        # parts[0] = prefix (may contain slashes if prefix has slashes – keep simple)
        if len(parts) < 5:
            return
        try:
            board_id = int(parts[1])
            io_type = parts[2]   # output / relay / led
            index = int(parts[3])
            value = 1 if payload in ("1", "ON", "on", "true", "True") else 0
        except (ValueError, IndexError):
            logger.warning("Unrecognised topic format: %s", topic)
            return

        board = self._boards.get(board_id)
        if board is None:
            logger.warning("No board with id %d", board_id)
            return

        try:
            if io_type == "output":
                board.output_pins[index].value = value
                self._publish(f"{prefix}/{board_id}/output/{index}/state", str(value))
            elif io_type == "relay":
                board.relays[index].value = value
                self._publish(f"{prefix}/{board_id}/relay/{index}/state", str(value))
                # Relays are wired to output pins 0/1 – echo on output topic too
                self._publish(f"{prefix}/{board_id}/output/{index}/state", str(value))
            elif io_type == "led":
                board.leds[index].value = value
                self._publish(f"{prefix}/{board_id}/led/{index}/state", str(value))
                # LEDs share the output register – echo on output topic too
                self._publish(f"{prefix}/{board_id}/output/{index}/state", str(value))
            else:
                logger.warning("Unknown io_type '%s' in topic %s", io_type, topic)
        except (IndexError, Exception) as exc:
            logger.error("Error setting %s/%d on board %d: %s", io_type, index, board_id, exc)

    # ------------------------------------------------------------------
    # Input listeners
    # ------------------------------------------------------------------

    def _start_listeners(self):
        for addr, board in self._boards.items():
            listener = pifacedigitalio.InputEventListener(chip=board, daemon=True)
            for pin in range(8):
                listener.register(pin, pifacedigitalio.IODIR_BOTH, self._make_input_callback(addr))
            listener.activate()
            self._listeners.append(listener)
            logger.debug("InputEventListener activated for board %d.", addr)

    def _make_input_callback(self, board_id: int):
        prefix = self._cfg.mqtt.topic_prefix

        def _callback(event):
            pin = event.pin_num
            value = event.direction  # 1 = pressed, 0 = released (IODIR_BOTH)
            # Read actual pin value for reliability
            board = self._boards[board_id]
            value = board.input_pins[pin].value
            self._input_state[board_id][pin] = value
            self._publish(f"{prefix}/{board_id}/input/{pin}/state", str(value))
            logger.debug("Board %d input %d changed to %d", board_id, pin, value)

        return _callback

    # ------------------------------------------------------------------
    # Initial state sync
    # ------------------------------------------------------------------

    def _publish_initial_states(self):
        prefix = self._cfg.mqtt.topic_prefix
        for board_id, board in self._boards.items():
            for pin in range(8):
                value = board.input_pins[pin].value
                self._publish(f"{prefix}/{board_id}/input/{pin}/state", str(value), retain=True)
            for pin in range(8):
                value = board.output_pins[pin].value
                self._publish(f"{prefix}/{board_id}/output/{pin}/state", str(value), retain=True)
            for relay in range(2):
                value = board.relays[relay].value
                self._publish(f"{prefix}/{board_id}/relay/{relay}/state", str(value), retain=True)
            for led in range(8):
                value = board.leds[led].value
                self._publish(f"{prefix}/{board_id}/led/{led}/state", str(value), retain=True)

    # ------------------------------------------------------------------
    # Discovery
    # ------------------------------------------------------------------

    def _publish_discovery(self):
        logger.info("Publishing Home Assistant MQTT discovery payloads…")
        for topic, payload in build_discovery_messages(self._cfg):
            self._publish(topic, payload, retain=True)

    # ------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------

    def _publish_online(self):
        self._publish(f"{self._cfg.mqtt.topic_prefix}/status", "online", retain=True)

    def _publish_offline(self):
        self._publish(f"{self._cfg.mqtt.topic_prefix}/status", "offline", retain=True)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _publish(self, topic: str, payload: str, retain: bool = False):
        result = self._client.publish(topic, payload, retain=retain)
        if result.rc != mqtt.MQTT_ERR_SUCCESS:
            logger.warning("Failed to publish to %s (rc=%d)", topic, result.rc)


def run(cfg: BridgeConfig):
    """Create and run the bridge; handle OS signals for clean shutdown."""
    bridge = PifaceMqttBridge(cfg)

    def _handle_signal(signum, frame):
        logger.info("Received signal %d, stopping…", signum)
        bridge._stop_event.set()

    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)

    bridge.start()
