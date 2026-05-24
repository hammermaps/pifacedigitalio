pifacedigitalio
===============
The PiFace Digital Input/Output module ([PyPI](https://pypi.python.org/pypi/pifacedigitalio/)).

Use this module to use PiFace Digital and PiFace Digital 2 hardware in Python 3

Install
=======

Make sure you are using the lastest version of Raspbian:

    $ sudo apt-get update
    $ sudo apt-get upgrade

Enable SPI (e.g. use raspi-config)

    $ sudo raspi-config
    
    select `Interface Options` > `SPI` > `Yes` and then select `Finish`

If you need to install pip3

    $ sudo apt install python3-pip

Install `pifacedigitalio` with the following command:

    Python 3:
    $ sudo pip3 install pifacedigitalio

 * Notice 1: Installation from Raspbian repository with apt is not longer the preferred way, take a look into [https://github.com/piface/pifacecommon/issues/27#issuecomment-451400154](issue 27)    
 * Notice 2: Python 2 support is "end-of-life" since Jan 2020, refer to https://www.python.org/doc/sunset-python-2/
 * Notice 3: Packaging metadata is maintained for modern Python 3 releases, including Python 3.14.

Examples
========

To run an example program clone this repo

    $ git clone https://github.com/piface/pifacedigitalio.git

Test by running the `blink.py` program:

    $ python3 pifacedigitalio/examples/blink.py

Documentation
=============

[http://pifacedigitalio.readthedocs.org/](http://pifacedigitalio.readthedocs.org/)

PiFace MQTT Bridge (Home Assistant)
====================================

`piface-mqtt.py` is a Python service that exposes all PiFace Digital I/Os over
MQTT so that the board can be integrated into [Home Assistant](https://www.home-assistant.io/)
(or any other MQTT-based automation system) with automatic device discovery.

### Features

- **8 inputs** published as `binary_sensor` entities in Home Assistant
- **8 outputs** published as `switch` entities, controllable via MQTT
- **2 relays** published as dedicated `switch` entities
- **8 LEDs** published as `light` entities
- **Interrupt-driven** input updates (no polling)
- **MQTT Discovery** – devices appear automatically in Home Assistant
- **systemd** service for reliable background operation
- **Multi-board** support (up to 4 PiFace Digital boards)

### MQTT Topic Schema

| Direction | Topic | Payload |
|-----------|-------|---------|
| PiFace → MQTT | `piface/{board}/input/{pin}/state` | `0` / `1` |
| MQTT → PiFace | `piface/{board}/output/{pin}/set` | `0` / `1` |
| PiFace → MQTT | `piface/{board}/output/{pin}/state` | `0` / `1` |
| MQTT → PiFace | `piface/{board}/relay/{relay}/set` | `0` / `1` |
| MQTT → PiFace | `piface/{board}/led/{led}/set` | `0` / `1` |
| Bridge status | `piface/status` | `online` / `offline` |

### Installation

1. **Install dependencies**

      $ sudo python3 -m pip install .

2. **Copy the configuration and service files to the target location**

      $ sudo mkdir -p /etc/piface-mqtt
      $ sudo cp config.example.yaml /etc/piface-mqtt/config.yaml
      $ sudo cp piface-mqtt.service /etc/systemd/system/

3. **Edit the configuration**

       $ sudo nano /etc/piface-mqtt/config.yaml

   At minimum, set `mqtt.broker` to your broker's IP address.

4. **Install and enable the systemd service**

      $ sudo systemctl daemon-reload
      $ sudo systemctl enable --now piface-mqtt

   If you want to run the service as a non-root account, set `User=` in
   `piface-mqtt.service` before enabling it.

5. **Check the service status**

       $ sudo systemctl status piface-mqtt
       $ journalctl -u piface-mqtt -f

### Manual run / Debugging

You can run the bridge directly from the command line without systemd:

    $ python3 piface-mqtt.py --config /etc/piface-mqtt/config.yaml

Add `--verbose` (or `-v`) to enable debug-level logging:

    $ python3 piface-mqtt.py --config /etc/piface-mqtt/config.yaml --verbose

### Running tests (no hardware required)

The MQTT bridge unit tests do **not** require SPI hardware and can be run anywhere:

    $ python3 -m pytest test_mqtt_bridge.py

### Configuration Reference

See `config.example.yaml` for all available options with comments.

| Key | Default | Description |
|-----|---------|-------------|
| `mqtt.broker` | `localhost` | MQTT broker hostname or IP |
| `mqtt.port` | `1883` | MQTT broker port |
| `mqtt.username` | *(empty)* | Broker username (optional) |
| `mqtt.password` | *(empty)* | Broker password (optional) |
| `mqtt.topic_prefix` | `piface` | Prefix for all MQTT topics |
| `mqtt.client_id` | `piface-mqtt` | MQTT client identifier |
| `mqtt.keepalive` | `60` | Keep-alive interval in seconds |
| `piface.boards` | `1` | Number of PiFace boards (1–4) |
| `piface.poll_interval` | `0.1` | Polling interval in seconds (reserved; currently unused) |
| `homeassistant.discovery` | `true` | Enable HA MQTT Discovery |
| `homeassistant.discovery_prefix` | `homeassistant` | HA discovery prefix |
