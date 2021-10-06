import typing
from collections.abc import Mapping
from dataclasses import dataclass, field, fields, is_dataclass
from enum import Enum


class LicenseTypes(Enum):
    per_server = "perServer"
    per_seat = "perSeat"


class Empty:
    pass


# todo: make it as an abstract class
class ObjectsList(list):
    OBJECT_CLASS = ""


@dataclass
class CustomizationSpecParams:
    def _get_all_nested_fields(self, obj):
        if is_dataclass(obj):
            for field in (getattr(obj, field.name) for field in fields(obj)):
                yield from self._get_all_nested_fields(field)
        else:
            yield obj

    def is_empty(self) -> bool:
        return not any(
            (field is not Empty for field in self._get_all_nested_fields(obj=self))
        )

    @classmethod
    def _set_instance_attributes(cls, instance, data):
        for key, val in data.items():
            instance_field = getattr(instance, key)

            if isinstance(val, Mapping):
                cls._set_instance_attributes(
                    instance=instance_field,
                    data=val,
                )
            elif isinstance(instance_field, ObjectsList):
                if val:
                    for obj_data in val:
                        obj_instance = instance_field.OBJECT_CLASS()
                        cls._set_instance_attributes(
                            instance=obj_instance,
                            data=obj_data,
                        )
                        instance_field.append(obj_instance)
                else:
                    setattr(instance, key, Empty)
            else:
                setattr(instance, key, val)

    @classmethod
    def from_dict(cls, data) -> "CustomizationSpecParams":
        instance = cls()
        cls._set_instance_attributes(instance=instance, data=data)
        return instance


@dataclass
class Network:
    use_dhcp: bool = Empty
    ipv4_address: str = Empty
    subnet_mask: str = Empty
    default_gateway: str = Empty
    alternate_gateway: str = Empty


class NetworksList(ObjectsList):
    OBJECT_CLASS = Network


@dataclass
class DNSSettings:
    primary_dns_server: str = Empty
    secondary_dns_server: str = Empty
    tertiary_dns_server: str = Empty
    dns_search_paths: typing.List[str] = Empty


@dataclass
class LinuxCustomizationSpecParams(CustomizationSpecParams):
    networks: NetworksList = field(default_factory=NetworksList)
    computer_name: str = Empty
    domain_name: str = Empty
    # timezone: str = Empty
    dns_settings: DNSSettings = field(default_factory=DNSSettings)


@dataclass
class RegistrationInfo:
    owner_name: str = Empty
    owner_organization: str = Empty


@dataclass
class License:
    product_key: str = field(default=Empty, repr=False)
    include_server_license_info: bool = Empty
    server_license_mode: LicenseTypes = Empty
    max_connections: int = Empty


@dataclass
class WindowsServerDomain:
    domain: str = Empty
    username: str = Empty
    password: str = field(default=Empty, repr=False)


@dataclass
class WindowsCustomizationSpecParams(CustomizationSpecParams):
    networks: NetworksList = field(default_factory=NetworksList)
    registration_info: RegistrationInfo = field(default_factory=RegistrationInfo)
    # timezone: str = Empty
    computer_name: str = Empty
    auto_logon: bool = Empty
    auto_logon_count: int = Empty
    license: License = field(default_factory=License)
    password: str = field(default=Empty, repr=False)
    commands_to_run_once: typing.List[str] = Empty
    workgroup: str = Empty
    windows_server_domain: WindowsServerDomain = field(
        default_factory=WindowsServerDomain
    )
