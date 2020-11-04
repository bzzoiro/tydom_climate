"""
Adds support for the Essent Icy E-Thermostaat units.
For more details about this platform, please refer to the documentation at
https://github.com/custom-components/climate.e_thermostaat
"""
import logging

import requests

from .tydum_api import system_info, set_temp, set_hvac


import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant.components.climate.const import (
    CURRENT_HVAC_HEAT,
    CURRENT_HVAC_IDLE,
    HVAC_MODE_HEAT,
    HVAC_MODE_OFF,
    SUPPORT_PRESET_MODE,
    SUPPORT_TARGET_TEMPERATURE,
)
from homeassistant.const import (
    ATTR_TEMPERATURE,
    CONF_PASSWORD,
    CONF_USERNAME,
    TEMP_CELSIUS,
)

try:
    from homeassistant.components.climate import (
        ClimateEntity,
        PLATFORM_SCHEMA,
    )
except ImportError:
    from homeassistant.components.climate import (
        ClimateDevice as ClimateEntity,
        PLATFORM_SCHEMA,
    )

__version__ = "0.0.1"

_LOGGER = logging.getLogger(__name__)


DEFAULT_NAME = "DeltaDore"

CONF_NAME = "name"
CONF_COMFORT_TEMPERATURE = "comfort_temperature"
CONF_SAVING_TEMPERATURE = "saving_temperature"
CONF_AWAY_TEMPERATURE = "away_temperature"

STATE_COMFORT = "Confort"  # "comfort"
STATE_SAVING = "Saving"  # "saving"
STATE_AWAY = "Away"  # "away"
STATE_FIXED_TEMP = "Fixed"  # "fixed temperature"

DEFAULT_COMFORT_TEMPERATURE = 22
DEFAULT_SAVING_TEMPERATURE = 18
DEFAULT_AWAY_TEMPERATURE = 14

# Values from web interface
MIN_TEMP = 14
MAX_TEMP = 28

# Values of E-Thermostaat to map to operation mode
COMFORT = 32
SAVING = 64
AWAY = 0
FIXED_TEMP = 128

SUPPORT_FLAGS = SUPPORT_PRESET_MODE | SUPPORT_TARGET_TEMPERATURE
SUPPORT_PRESET = [STATE_AWAY, STATE_COMFORT, STATE_FIXED_TEMP, STATE_SAVING]

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
        vol.Required(CONF_USERNAME): cv.string,
        vol.Required(CONF_PASSWORD): cv.string,
        vol.Optional(
            CONF_AWAY_TEMPERATURE, default=DEFAULT_AWAY_TEMPERATURE
        ): vol.Coerce(float),
        vol.Optional(
            CONF_SAVING_TEMPERATURE, default=DEFAULT_SAVING_TEMPERATURE
        ): vol.Coerce(float),
        vol.Optional(
            CONF_COMFORT_TEMPERATURE, default=DEFAULT_COMFORT_TEMPERATURE
        ): vol.Coerce(float),
    }
)


def setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up the E-Thermostaat platform."""
    name = config.get(CONF_NAME)
    comfort_temp = config.get(CONF_COMFORT_TEMPERATURE)
    saving_temp = config.get(CONF_SAVING_TEMPERATURE)
    away_temp = config.get(CONF_AWAY_TEMPERATURE)
    username = config.get(CONF_USERNAME)
    password = config.get(CONF_PASSWORD)

    add_entities(
        [DeltaDoreClimate(name, username, password, comfort_temp, saving_temp, away_temp)]
    )


class DeltaDoreClimate(ClimateEntity):
    """Representation of a DeltaDore device."""

    def __init__(self, name, username, password, comfort_temp, saving_temp, away_temp):
        """Initialize the thermostat."""
        self._name = name
        self._username = username
        self._password = password

        self._comfort_temp = comfort_temp
        self._saving_temp = saving_temp
        self._away_temp = away_temp

        self._current_temperature = 0
        self._target_temperature = 0
        self._old_conf = None
        self._current_operation_mode = None

        self._device_id = None
        self._token = None
        
        self._host = 'mediation.tydom.com'
        self._data = None

        self.update()
        
    @property
    def payload(self):
        """Return the payload."""
        return {'username': self._username, 'password': self._password, 'host': self._host}

    @property
    def name(self):
        """Return the name of the thermostat."""
        return self._name

    @property
    def unique_id(self) -> str:
        """Return the unique ID for this thermostat."""
        return "_".join([self._name, "climate"])

    @property
    def should_poll(self):
        """Return if polling is required."""
        return True

    @property
    def min_temp(self):
        """Return the minimum temperature."""
        return MIN_TEMP

    @property
    def max_temp(self):
        """Return the maximum temperature."""
        return MAX_TEMP

    @property
    def temperature_unit(self):
        """Return the unit of measurement."""
        return TEMP_CELSIUS

    @property
    def current_temperature(self):
        """Return the current temperature."""
        return self._current_temperature

    @property
    def target_temperature(self):
        """Return the temperature we try to reach."""
        return self._target_temperature

    @property
    def hvac_mode(self):
        """Return hvac operation ie. heat, cool mode."""
        return HVAC_MODE_HEAT

    @property
    def hvac_modes(self):
        """HVAC modes."""
        return [HVAC_MODE_OFF, HVAC_MODE_HEAT]

    @property
    def hvac_action(self):
        """Return the current running hvac operation."""
        try:
            if self._target_temperature < self._current_temperature:
                return CURRENT_HVAC_IDLE
            return CURRENT_HVAC_HEAT
        except:
            _LOGGER.debug("Error at hvac_action")
            return CURRENT_HVAC_IDLE

    @property
    def preset_mode(self):
        """Return the current preset mode, e.g., home, away, temp."""
        return self._current_operation_mode

    @property
    def preset_modes(self):
        """Return a list of available preset modes."""
        return SUPPORT_PRESET

    @property
    def is_away_mode_on(self):
        """Return true if away mode is on."""
        return self._current_operation_mode in [STATE_AWAY]

    @property
    def supported_features(self):
        """Return the list of supported features."""
        return SUPPORT_FLAGS

    def set_preset_mode(self, preset_mode: str):
        """Set new preset mode."""
        if preset_mode == STATE_COMFORT:
            self._set_temperature(self._comfort_temp, mode_int=COMFORT)
        elif preset_mode == STATE_SAVING:
            self._set_temperature(self._saving_temp, mode_int=SAVING)
        elif preset_mode == STATE_AWAY:
            self._set_temperature(self._away_temp, mode_int=AWAY)
        elif preset_mode == STATE_FIXED_TEMP:
            self._set_temperature(self._target_temperature, mode_int=FIXED_TEMP)

    def set_temperature(self, **kwargs):
        """Set new target temperature."""
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is None:
            return
        self._set_temperature(temperature)
        
    def set_hvac_mode(self, hvac_mode):
        
        if (hvac_mode == HVAC_MODE_OFF):
            set_hvac(self._device_id, 'STOP', self.payload)
        if (hvac_mode == HVAC_MODE_HEAT):
            set_hvac(self._device_id, 'HEATING', self.payload)
    
    def _set_temperature(self, temperature, mode_int=None):
        """Set new target temperature, via URL commands."""
        self._target_temperature = temperature
        set_temp(self._device_id, temperature, self.payload)
    
    
    def _get_data(self):
        """Get the data of the Delta Dore."""
        self._data = system_info(self.payload)
        data = self._data
        if self._data:
            self._target_temperature = data.get('setpoint', data['temperature'])
            self._current_temperature = data['temperature']
            
            _dict = {'STOP': 'Off', 'HEATING': 'On'}
            self._current_operation_mode = _dict.get(data['authorization'], 'Unkown')
            self._device_id = data['endpoint']
            _LOGGER.debug("Delta Dore value: {}".format(self._target_temperature, self._current_temperature))
        else:
            _LOGGER.error("Could not get data from Tydum. {}".format(self._data))


    def update(self):
        """Get the latest data."""
        self._get_data()
