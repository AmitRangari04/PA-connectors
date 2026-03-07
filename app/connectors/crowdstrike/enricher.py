from glom import glom, Coalesce, T


class Enricher:

    def enrich(self, r, name):
        endpoints = {
            'cs_apps':
                {
                    "type": Coalesce(T["type"], default="installed_app"),
                    "tenant": "tenant",
                    "device_id": "device_id",
                    "app_name": "name",
                    "version": "version",
                    "vendor": "vendor"
                },
            'cs_devices': {
                "type": Coalesce(T["type"], default="device"),
                "id": "cid",
                "tenant": "tenant",
                "time_generated": "agent_local_time",
                "log_source_id": "device_id",
                "source_device_host": "hostname",
                "source_device_vendor": "system_manufacturer",
                "source_device_model": "system_product_name",
                "source_device_os": "platform_name",
                "source_device_osfamily": "product_type_desc",
                "source_device_mac": "mac_address",
                "platform": "platform_name",
                "source_device_osversion": "os_version",
                "agent_version": "agent_version",
                "source_ip": "external_ip",
                "local_ip": "local_ip",
                "first_seen": "first_seen",
                "last_seen": "last_seen",
            },
            'cs_processes': {
                "type": Coalesce(T["type"], default="process"),
                "tenant": "tenant",
                "device_id": "device_id",
                "process_name": "process_name",
                "command_line": "command_line"
            },
            'cs_users': {
                "type": Coalesce(T["type"], default="user"),
                "tenant": "tenant",
                "user_id": "user_id",
                "username": "username",
                "email": "email",
                "roles": "roles",
                "groups": "groups"
            },
            'cs_vulns': {
                "type": Coalesce(T["type"], default="vulnerability"),
                "tenant": "tenant",
                "cve": "cve_id",
                "severity": "severity",
                "hostname": "hostname"
            }
        }
        spec = endpoints.get(name)

        return glom(r, spec)
