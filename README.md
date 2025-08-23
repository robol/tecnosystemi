# Tecnosystemi integration for Home Assistant
Home Assistant integration for [Tecnosystemi](https://www.tecnosystemi.com) zoned air conditioning systems.

This integration allows to control zoned air conditioning systems that have already been configured with
the Tecnosystemi [Android](https://play.google.com/store/apps/details?id=it.tecnosystemi.TS) or 
[iOS app](https://apps.apple.com/it/app/tecnosystemi/id6450835877). 
The integration uses the same API endpoints of the apps, and both can be used at the same time.

## How to install

The easiest installation method is to use [HACS](https://www.hacs.xyz/). If your Home Assistant 
instance has HACS already configured, you can add the custom repository ```robol/tecnosystemi```, 
and then you will find the integration directly in HACS.

Otherwise, you can copy the ``custom_components/tecnosystemi`` folder from 
this repository inside the ``config/custom_components/`` folder of your Home Assistant instance. 
If you do not have a ``custom_components`` folder, simply create a new one.

## How to configure a new instance
Go to Settings -> Integrations and add a new Tecnosystemi instance. It will asks for username 
and password, and a PIN. The PIN is the one that you set up using the Android (or iOS) apps, 
and the same PIN is used across all Tecnosystemi systems (if you have more than one). 

## Supported systems

 * Polaris 5X

Maybe other versions could work, but I have not tested them. Feel free to reach out in case you 
get it working. 
