import os
import tempfile
import unittest
from types import SimpleNamespace
from unittest import mock

import paho.mqtt.client as mqtt

from piface_mqtt.bridge import PifaceMqttBridge
from piface_mqtt.config import BridgeConfig, HomeAssistantConfig, MqttConfig, PifaceConfig, load_config
from piface_mqtt.discovery import build_discovery_messages


class _FakePin:
    def __init__(self, value=0):
        self.value = value


class _FakeBoard:
    def __init__(self):
        self.input_pins = [_FakePin() for _ in range(8)]
        self.output_pins = [_FakePin() for _ in range(8)]
        self.relays = [_FakePin() for _ in range(2)]
        self.leds = [_FakePin() for _ in range(8)]
        self.deinitialised = False

    def deinit_board(self):
        self.deinitialised = True


class _FakePublishResult:
    def __init__(self):
        self.rc = mqtt.MQTT_ERR_SUCCESS
        self.waited = False

    def wait_for_publish(self):
        self.waited = True


class _FakeClient:
    def __init__(self):
        self.subscriptions = []
        self.published = []
        self.disconnect_called = False
        self.loop_stop_called = False
        self.last_result = None

    def subscribe(self, topic):
        self.subscriptions.append(topic)

    def publish(self, topic, payload, retain=False):
        self.last_result = _FakePublishResult()
        self.published.append((topic, payload, retain, self.last_result))
        return self.last_result

    def disconnect(self):
        self.disconnect_called = True

    def loop_stop(self):
        self.loop_stop_called = True


class LoadConfigTests(unittest.TestCase):
    def test_load_config_accepts_string_false(self):
        with tempfile.NamedTemporaryFile("w", delete=False) as handle:
            handle.write("homeassistant:\n  discovery: 'false'\n")
            path = handle.name

        try:
            cfg = load_config(path)
        finally:
            os.unlink(path)

        self.assertFalse(cfg.homeassistant.discovery)

    def test_load_config_rejects_invalid_boolean(self):
        with tempfile.NamedTemporaryFile("w", delete=False) as handle:
            handle.write("homeassistant:\n  discovery: maybe\n")
            path = handle.name

        try:
            with self.assertRaisesRegex(ValueError, "homeassistant.discovery"):
                load_config(path)
        finally:
            os.unlink(path)


class DiscoveryTests(unittest.TestCase):
    def test_build_discovery_messages_uses_topic_prefix(self):
        cfg = BridgeConfig(
            mqtt=MqttConfig(topic_prefix="site/piface"),
            piface=PifaceConfig(boards=1),
            homeassistant=HomeAssistantConfig(discovery_prefix="ha"),
        )

        messages = build_discovery_messages(cfg)

        self.assertEqual(len(messages), 26)
        self.assertIn(
            (
                "ha/switch/piface_0_output_0/config",
                mock.ANY,
            ),
            messages,
        )
        self.assertIn('"state_topic": "site/piface/0/output/0/state"', messages[8][1])


class BridgeTests(unittest.TestCase):
    def setUp(self):
        cfg = BridgeConfig(
            mqtt=MqttConfig(topic_prefix="site/piface"),
            piface=PifaceConfig(boards=1),
            homeassistant=HomeAssistantConfig(discovery=True),
        )
        self.bridge = PifaceMqttBridge(cfg)
        self.bridge._client = _FakeClient()
        self.bridge._boards = {0: _FakeBoard()}
        self.bridge._input_state = {0: [0] * 8}

    def test_on_connect_publishes_online_discovery_and_initial_state(self):
        with mock.patch("piface_mqtt.bridge.build_discovery_messages", return_value=[("ha/topic", "{}")]):
            self.bridge._on_connect(self.bridge._client, None, None, 0)

        self.assertIn("site/piface/0/output/+/set", self.bridge._client.subscriptions)
        published_topics = [topic for topic, _, _, _ in self.bridge._client.published]
        self.assertIn("site/piface/status", published_topics)
        self.assertIn("ha/topic", published_topics)
        self.assertIn("site/piface/0/input/0/state", published_topics)

    def test_on_message_parses_prefix_with_slashes(self):
        msg = SimpleNamespace(topic="site/piface/0/output/3/set", payload=b"ON")

        self.bridge._on_message(self.bridge._client, None, msg)

        self.assertEqual(self.bridge._boards[0].output_pins[3].value, 1)
        self.assertIn(
            ("site/piface/0/output/3/state", "1", False, self.bridge._client.last_result),
            self.bridge._client.published,
        )

    def test_on_message_ignores_invalid_payload(self):
        msg = SimpleNamespace(topic="site/piface/0/output/3/set", payload=b"toggle")

        self.bridge._on_message(self.bridge._client, None, msg)

        self.assertEqual(self.bridge._boards[0].output_pins[3].value, 0)
        self.assertEqual(self.bridge._client.published, [])

    def test_input_callback_suppresses_duplicate_publishes(self):
        callback = self.bridge._make_input_callback(0)
        event = SimpleNamespace(pin_num=2, direction=1)

        self.bridge._boards[0].input_pins[2].value = 1
        callback(event)
        callback(event)

        published_topics = [topic for topic, _, _, _ in self.bridge._client.published]
        self.assertEqual(published_topics.count("site/piface/0/input/2/state"), 1)

    def test_stop_waits_for_offline_publish(self):
        self.bridge.stop()

        self.assertTrue(self.bridge._client.last_result.waited)
        self.assertTrue(self.bridge._client.disconnect_called)
        self.assertTrue(self.bridge._client.loop_stop_called)


if __name__ == "__main__":
    unittest.main()
