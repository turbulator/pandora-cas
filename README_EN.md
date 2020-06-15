[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/custom-components/hacs)
[![Donate](https://img.shields.io/badge/donate-Yandex-orange.svg)](https://money.yandex.ru/to/41001690673042)

# Home Assistant custom component for Pandora Car Alarm System

[Русский](https://github.com/turbo-lab/pandora-cas/blob/master/README.md) | **English**

![Pandora](https://raw.githubusercontent.com/turbo-lab/pandora-cas/master/images/pandora.gif)

This component was made for control and automate your cars which are equipped with Pandora Car Alarm System, one of the most popular Car Alarm System in Russia. Once configured it will detect and add all your cars into Home Assistant.

This integration uses the unofficial API used in the official Pandora website ```https://p-on.ru```, and you will need to use the same Username and Password you use on the Pandora website to configure this integration in Home Assistant.

This integration provides the following platforms:

- [Device Tracker](#device-tracker): The location of your car.
- [Sensors and Binary Sensors](#sensors): The temperature, Speed, Doors, Engine's state, etc.
- [Services](#services): Like Lock/Unlock, Start/Stop

## Installation

1. Install [HACS](https://hacs.xyz/docs/installation/manual)
1. Go to Custom repositories management tab of HACS and add URL of this repo ```https://github.com/turbo-lab/pandora-cas``` as an Integration
1. Install Pandora Car Alarm System component
1. Configure component via configuration.yaml (see instructions below)
1. Restart the Home Assistant

## Configuration

Now add the following lines to your `configuration.yaml` file:

```yaml
# Example configuration.yaml entry
pandora-cas:
  username: YOUR_USERNAME
  password: YOUR_PASSWORD
```

Configuration variables:

```yaml
pandora-cas:
  (map) (Optional) Configuration options for Pandora Car Alarm System integration.

  username:
    (string)(Required) description: Your username from p-on.ru.

  password:
    (string)(Required) description: Your password from p-on.ru.

  polling_interval:
    (integer)(Optional) description: The time in seconds between updates from Pandora's website. Default value: 60s

```

## Device Tracker

TBD

## Sensors

TBD

## Services

TBD

## Disclimer

This software is unofficial and isn't affiliated with or endorsed by ООО «НПО Телеметрия». You can use it at own risk.

All brand and/or product names are trademarks of their respective owners.
