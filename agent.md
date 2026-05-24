# Agent Context: pifacedigitalio

## Projektüberblick
- Python-Bibliothek zur Ansteuerung von **PiFace Digital** / **PiFace Digital 2** Hardware.
- Fokus auf GPIO-I/O über den MCP23S17-Chip via SPI.
- Paketname: `pifacedigitalio`, Abhängigkeit: `pifacecommon==4.0.0`.

## Kernstruktur
- `pifacedigitalio/core.py`: Hauptlogik, Board-Initialisierung, Wrapper-Funktionen (`digital_read`, `digital_write`), Interrupt-Listener.
- `pifacedigitalio/__init__.py`: Re-Export von `core` + Interrupt-Richtungs-Konstanten.
- `tests.py`: Unittests/Integrationstests (teils interaktiv und hardwareabhängig).
- `docs/`: Sphinx-Dokumentation (Installation, Referenz, Beispiele).
- `setup.py`: Packaging-Metadaten.

## Architektur in Kürze
- Zentrale Klasse: `PiFaceDigital`, erbt von `pifacecommon.mcp23s17.MCP23S17` und `GPIOInterruptDevice`.
- `PiFaceDigital` mappt:
  - 8 Eingänge (`input_pins`) + Input-Port
  - 8 Ausgänge (`output_pins`) + Output-Port
  - 8 LEDs (`leds`)
  - 2 Relais (`relays`)
  - 4 Schalter (`switches`)
- Multi-Board-Support bis 4 Boards über Hardware-Adresse (`MAX_BOARDS = 4`).

## Lauf- und Testhinweise
- Tests benötigen SPI-Gerät (`/dev/spidev0.0`) und damit reale/konfigurierte Hardware.
- Ohne Hardware schlagen Tests in dieser Umgebung erwartbar fehl (`SPIInitError`).

## Wartungsrelevante Hinweise
- Python-2-Kompatibilitätsreste sind noch vorhanden (historisch), Projekt ist aber auf Python 3 nutzbar.
- Bei Änderungen an I/O- oder Interrupt-Logik sollten Hardware-nahe Tests auf Raspberry Pi mit aktivem SPI erfolgen.
