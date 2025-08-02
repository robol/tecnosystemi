# Tecnosystemi integration for Home Assistant
This repository contains a Home Assistant integration to support the air conditioning 
management systems from [Tecnosystemi](https://www.tecnosystemi.com), an Italian company.

The support uses the API endpoints used by the Android and iOS apps, which are not 
publicly documented. The protocol has been reverse-engineered starting from the 
apps themselves. 

This integration should be considered in an **alpha** state at the moment: it works 
with my setup, that consists in a [Polaris 5X](https://www.tecnosystemi.com/en/pro/products/galaxy/proair-multi-zone-control-system/polaris-5x-wi-fi-single-control-unit-with-colour-display-communication-protocols-and-alexa-app-google-home?related=1&origin=https%3A%2F%2Fwww.tecnosystemi.com%2Fen%2Fpro%2Fproducts%2Fgalaxy%2Fproair-multi-zone-control-system)
 in a [ProAir](https://www.tecnosystemi.com/en/pro/products/galaxy/proair-multi-zone-control-system) 
system (referred to as the [Galaxy series](https://www.tecnosystemi.com/en/pro/products/galaxy/proair-multi-zone-control-system)).

## What is working
I will list here the configurations that are known to be working. Right now that is only mine, 
but feel free to report success stories and/or feedback. Other products may be supported, but
I will need help from people actually owning the hardware.

 * ProAir system with Polaris 5X.

## How to install
Installing the integration requires to copy the ``custom_components/tecnosystemi`` folder from 
this repository inside the ``config/custom_components/`` folder of your Home Assistant instance. 
If you do not have a ``custom_components`` folder, simply create a new one.

## How to configure a new instance
Go to Settings -> Integrations and add a new Tecnosystemi instance. It will asks for username 
and password, and a PIN. The PIN is the one that you set up using the Android (or iOS) apps, 
and the same PIN is used across all Tecnosystemi systems (if you have more than one). 

## TODO List

 * Support different systems with different PINs, that should be asked interactively
   when the systems are discovered.
