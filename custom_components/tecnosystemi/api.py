"""API Client for Tecnosystemi integration."""

from __future__ import annotations

import asyncio
import base64
import hashlib
import json
import time

import aiohttp
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes


class Device:
    """Represents a device in the Tecnosystemi system."""

    def __init__(self, data):
        """Initialize the device with data from the API."""
        self.LVDV_Type = data.get("LVDV_Type")
        self.LVDV_Id = data.get("LVDV_Id")
        self.DevId = data.get("DevId")
        self.Serial = data.get("Serial")
        self.Name = data.get("Name")
        self.FWVer = data.get("FWVer")
        self.OperatingMode = data.get("OperatingMode")
        self.IsOff = data.get("IsOff")
        self.LastConfigUpd = data.get("LastConfigUpd")
        self.LastSyncUpd = data.get("LastSyncUpd")
        self.LastAddTimezone = data.get("LastAddTimezone")
        self.NUM_ERROR = data.get("NUM_ERROR")

    def to_dict(self):
        """Return a dict representation of the device."""
        return {
            "LVDV_Type": self.LVDV_Type,
            "LVDV_Id": self.LVDV_Id,
            "DevId": self.DevId,
            "Serial": self.Serial,
            "Name": self.Name,
            "FWVer": self.FWVer,
            "OperatingMode": self.OperatingMode,
            "IsOff": self.IsOff,
            "LastConfigUpd": self.LastConfigUpd,
            "LastSyncUpd": self.LastSyncUpd,
            "LastAddTimezone": self.LastAddTimezone,
            "NUM_ERROR": self.NUM_ERROR,
        }


class Plant:
    """Represents a plant in the Tecnosystemi system."""

    def __init__(self, data):
        """Initialize the plant with data from the API."""
        self.LVPL_Id = data.get("LVPL_Id")
        self.LVPL_Name = data.get("LVPL_Name")
        self.LVPL_USAN_Id = data.get("LVPL_USAN_Id")
        self.LVPL_Icon = data.get("LVPL_Icon")
        self.ListDevices = [Device(d) for d in data.get("ListDevices", [])]

    def getDevices(self):
        """Return the list of devices in this plant."""
        return self.ListDevices

    def to_dict(self):
        """Return a dict representation of the plant, including devices."""
        return {
            "LVPL_Id": self.LVPL_Id,
            "LVPL_Name": self.LVPL_Name,
            "LVPL_USAN_Id": self.LVPL_USAN_Id,
            "LVPL_Icon": self.LVPL_Icon,
            "ListDevices": [device.to_dict() for device in self.ListDevices],
        }


class AESTool:
    """AES encryption/decryption utility for Tecnosystemi API."""

    def __init__(self, salt: str) -> None:
        """Initialize the AES tool with a salt."""
        # Derive 256-bit key using SHA-256
        digest = hashlib.sha256(salt.encode("utf-8")).digest()
        self.key = digest  # Already 32 bytes for AES-256
        self.iv = bytes([0] * 16)  # 16 null bytes as IV
        self.backend = default_backend()

    def encrypt(self, plaintext: str) -> str:
        """Encrypt the plaintext using AES in CBC mode."""
        padder = padding.PKCS7(128).padder()
        padded_data = padder.update(plaintext.encode("utf-8")) + padder.finalize()

        cipher = Cipher(
            algorithms.AES(self.key), modes.CBC(self.iv), backend=self.backend
        )
        encryptor = cipher.encryptor()
        encrypted = encryptor.update(padded_data) + encryptor.finalize()

        return base64.b64encode(encrypted).decode("utf-8")

    def decrypt(self, ciphertext: str) -> str:
        """Decrypt the ciphertext using AES in CBC mode."""
        encrypted_data = base64.b64decode(ciphertext)

        cipher = Cipher(
            algorithms.AES(self.key), modes.CBC(self.iv), backend=self.backend
        )
        decryptor = cipher.decryptor()
        decrypted_padded = decryptor.update(encrypted_data) + decryptor.finalize()

        unpadder = padding.PKCS7(128).unpadder()
        decrypted = unpadder.update(decrypted_padded) + unpadder.finalize()

        return decrypted.decode("utf-8")


class TecnosystemiAPI:
    """Client for interacting with the Tecnosystemi cloud API."""

    def __init__(self, device_id, username, password):
        """Initialize the API client with credentials and device ID."""
        self.salt = base64.b64decode(b'bnM5MXdyNDg=').decode("utf-8")
        self.fix_token = base64.b64decode(b'R2E1bU02MUtDbTVCazE4bGhENUo5OTlqQzJNdTBWYWY=').decode("utf-8")
        self.device_id = device_id
        self.username = username
        self.password = password
        self.base_url = "https://proair.azurewebsites.net"
        self.token = None
        self.counter = 0
        self.token_expiry = 0  # This is a timestamp for when the token expires
        self.user_id = None
        self.session = aiohttp.ClientSession()

        # Since the calls to the API needs to be done sequentially, we use a lock
        # for these tasks, ensuring that there is no overlapping.
        self.api_lock = asyncio.Lock()

    def getAESTool(self):
        """Return an instance of AESTool for encryption/decryption."""
        return AESTool(self.device_id[0:8] + self.salt)

    def storeToken(self, token):
        """Store the token and counter from the encrypted token."""
        splitted_token = self.getAESTool().decrypt(token).split("_")
        if len(splitted_token) == 2:
            self.token = splitted_token[0]
            self.counter = int(splitted_token[1])

            # It is currently not documented what the token expiry time is,
            # but in practice it seems to be a few hours; hence, we renew it
            # after 1 hour to be on the safe side.
            #
            # Update: it appears that the token expiry is 3 hours. We still
            # set it to 1 hour for safety.
            self.token_expiry = time.time() + 3600
        else:
            raise ValueError("Invalid token format")

    async def calcToken(self):
        """Calculate the new token using the stored token and counter."""
        if self.token is None:
            return None

        # If the token is expired, we need to perform a new login
        if time.time() >= self.token_expiry:
            await self.login()

            # In case the login fails and token cannot be obtained,
            # we just return None to mean that the API is not available
            if self.token is None:
                return None

        self.counter += 1  # Increment the counter for each token calculation

        # Calculate the token using the stored token and counter
        return self.getAESTool().encrypt(f"{self.token}_{self.counter}")

    async def GetPlants(self):
        """Get the list of plants from the Tecnosystemi API."""
        token = await self.calcToken()
        if token is None:
            raise RuntimeError("Token is not available")
        url = self.base_url + "/api/v1/GetPlants"
        auth = aiohttp.BasicAuth(self.username, "PwdProAir")
        headers = {"Token": token}
        async with self.session.get(url, auth=auth, headers=headers) as response:
            response_data = await response.json()
            if response.status == 200 and response_data.get("ResCode") == 0:
                return [
                    Plant(x) for x in json.loads(response_data.get("ResDescr", "[]"))
                ]
            return []

    async def getDeviceState(self, device, pin):
        """Get the state of a specific device."""
        token = await self.calcToken()
        if token is None:
            raise RuntimeError("Token is not available")
        url = self.base_url + f"/api/v1/GetCUState?cuSerial={device.Serial}&PIN={pin}"
        auth = aiohttp.BasicAuth(self.username, "PwdProAir")
        headers = {"Token": token}
        async with (
            self.api_lock,
            self.session.get(url, auth=auth, headers=headers) as response,
        ):
            if response.status == 200:
                return await response.json()
            return None

    async def updateCUState(self, device, pin, cmd):
        """Update the state of a specific device (globally across different zones)."""
        token = await self.calcToken()
        if token is None:
            raise RuntimeError("Token is not available")

        cmd["c"] = "upd_cu"
        cmd["pin"] = pin
        if "is_off" not in cmd:
            cmd["is_off"] = 0
        if "is_cool" not in cmd:
            cmd["is_cool"] = 1
        if "cool_mod" not in cmd:
            cmd["cool_mod"] = 1
        if "t_can" not in cmd:
            cmd["t_can"] = 230

        # I suspect that these two are related to winter (inverno) and summer (estate).
        # they appear to be always set to 1 in the API, at least on my machine.
        cmd["f_inv"] = 1
        cmd["f_est"] = 1

        data = {
            "Serial": device.Serial,
            "Name": device.Name,
            "Pin": pin,
            "Cmd": json.dumps(cmd),
        }

        url = self.base_url + "/api/v1/UpdateCUData"
        auth = aiohttp.BasicAuth(self.username, "PwdProAir")
        headers = {"Token": token, "Content-Type": "application/json"}
        async with (
            self.api_lock,
            self.session.post(url, json=data, auth=auth, headers=headers) as response,
        ):
            if response.status == 200:
                response_data = await response.json()
                if response_data.get("ResCode") == 0:
                    return True
                raise RuntimeError(
                    f"Update failed with error code: {response_data.get('ResCode')}"
                )
            raise RuntimeError(
                f"Update failed with HTTP status code: {response.status}"
            )

    async def updateDeviceState(self, device, pin, zoneid, cmd):
        """Update the state of a specific zone in the device."""
        token = await self.calcToken()
        if token is None:
            raise RuntimeError("Token is not available")

        cmd["id_zona"] = zoneid
        cmd["pin"] = pin
        cmd["c"] = "upd_zona"
        if "shu_set" not in cmd:
            cmd["shu_set"] = "0"
        if "fan_set" not in cmd:
            cmd["fan_set"] = "0"
        if "is_crono" not in cmd:
            cmd["is_crono"] = 0

        data = {
            "Serial": device.Serial,
            "Pin": pin,
            "ZoneId": zoneid,
            "Name": device.Name,
            "Cmd": json.dumps(cmd),
        }

        url = self.base_url + "/api/v1/UpdateZonaData"
        auth = aiohttp.BasicAuth(self.username, "PwdProAir")
        headers = {"Token": token, "Content-Type": "application/json"}
        async with (
            self.api_lock,
            self.session.post(url, json=data, auth=auth, headers=headers) as response,
        ):
            if response.status == 200:
                response_data = await response.json()
                if response_data.get("ResCode") == 0:
                    return True
                raise RuntimeError(
                    f"Update failed with error code: {response_data.get('ResCode')}"
                )
            raise RuntimeError(
                f"Update failed with HTTP status code: {response.status}"
            )

    async def login(self):
        """Login to the Tecnosystemi API."""
        password = self.getAESTool().encrypt(self.password)

        data = {
            "DeviceId": self.device_id,
            "Platform": "fcm2",
            "Password": password,
            "TokenPush": None,
            "Username": self.username,
        }

        url = self.base_url + "/apiTS/v2/Login"
        auth = aiohttp.BasicAuth("UsrProAir", "PwdProAir")
        headers = {"Token": self.fix_token, "Content-Type": "application/json"}
        async with (
            self.api_lock,
            self.session.post(url, json=data, auth=auth, headers=headers) as response,
        ):
            if response.status == 200:
                login_data = await response.json()
                if login_data.get("ResCode") != 0:
                    raise RuntimeError(
                        f"Login failed with error code: {login_data.get('ResCode')}"
                    )
                self.user_id = login_data.get("ID")
                self.storeToken(login_data.get("Token"))
                return True
            raise RuntimeError(f"Login failed with status code: {response.status}")
