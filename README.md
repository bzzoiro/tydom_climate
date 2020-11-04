[![Version](https://img.shields.io/badge/version-0.0.1-green.svg?style=for-the-badge)](#)
[![mantained](https://img.shields.io/maintenance/yes/2020.svg?style=for-the-badge)](#)
[![maintainer](https://img.shields.io/badge/maintainer-%20%40bzzoiro-blue.svg?style=for-the-badge)](#)

### This component only works on HA 0.96 and later.

# Custom component for Tydom / Delta Dore
A platform which allows you to interact with the Delta Dore Thermostast.

## Current Features
- Read thermostat temperature.
- Set Temperature
- On / Off
- Preset : Away / Boost Mode / Eco Mode / Standard Mode

## Installation
Install the component manually by putting the files from `/custom_components/tydom_climate/` in your folder `<config directory>/custom_components/tydom_climate/` 

## Screenshot
Tydom Climate

![alt text](https://i.ibb.co/rMJbfQy/Capture.png)

![alt text](https://i.ibb.co/DGSYhxJ/Capture2.png)

## Configuration
**Example configuration.yaml:**

```yaml
climate:
  - platform: tydom_climate
    username: Tydom Mac Addresss
    password: Tydom Password
    comfort_temperature: 20
    eco_temperature: 17
    away_temperature: 12
```

**Configuration variables:**  
  
key | description  
:--- | :---  
**platform (Required)** | The platform name.
**username (Required)** | The MAC of your Tydom/Delta Dore account.
**password (Required)** | The password of your Tydom/Delta Dore account.
**comfort_temperature (Optional)** | The comfort temperature defaults to 20.  
**saving_temperature (Optional)** | The saving temperature defaults to 17.  
**away_temperature (Optional)** | The away temperature defaults to 12.  


This platform is using the [Tydom API](https://www.deltadore.co.uk/) to get the information from the thermostat.

Based on https://github.com/custom-components/climate.e_thermostaat
