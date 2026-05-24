#!/usr/bin/env python3
"""PiFace Digital MQTT Bridge – entry point."""

import argparse
import logging
import sys

from piface_mqtt.config import load_config
from piface_mqtt.bridge import run


def _setup_logging(verbose: bool):
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )


def main():
    parser = argparse.ArgumentParser(
        description="PiFace Digital MQTT Bridge for Home Assistant"
    )
    parser.add_argument(
        "--config",
        "-c",
        default="/etc/piface-mqtt/config.yaml",
        metavar="FILE",
        help="Path to YAML configuration file (default: /etc/piface-mqtt/config.yaml)",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable debug logging",
    )
    args = parser.parse_args()

    _setup_logging(args.verbose)
    logger = logging.getLogger("piface-mqtt")

    try:
        cfg = load_config(args.config)
    except FileNotFoundError:
        logger.error("Configuration file not found: %s", args.config)
        sys.exit(1)
    except Exception as exc:
        logger.error("Failed to load configuration: %s", exc)
        sys.exit(1)

    try:
        run(cfg)
    except Exception as exc:
        logger.critical("Fatal error: %s", exc, exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
