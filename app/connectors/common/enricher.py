class Enricher:

    def enrich(self, r, name):
        endpoints = {
            'cs_apps':
                {
                    "type": "installed_app",
                    "tenant": r.get("tenant"),
                    "device_id": r.get("device_id"),
                    "app_name": r.get("name"),
                    "version": r.get("version"),
                    "vendor": r.get("vendor")
                },
            'cs_devices': {
                "type": "device",
                "tenant": r.get("tenant"),
                "device_id": r.get("device_id"),
                "hostname": r.get("hostname"),
                "platform": r.get("platform_name"),
                "os_version": r.get("os_version"),
                "agent_version": r.get("agent_version"),
                "external_ip": r.get("external_ip"),
                "local_ip": r.get("local_ip"),
                "first_seen": r.get("first_seen"),
                "last_seen": r.get("last_seen")
            },
            'cs_processes': {
                "type": "process",
                "tenant": r.get("tenant"),
                "device_id": r.get("device_id"),
                "process_name": r.get("process_name"),
                "command_line": r.get("command_line")
            },
            'cs_users': {
                "type": "user",
                "tenant": r.get("tenant"),
                "user_id": r.get("user_id"),
                "username": r.get("username"),
                "email": r.get("email"),
                "roles": r.get("roles"),
                "groups": r.get("groups")
            },
            'cs_vulns': {
                "type": "vulnerability",
                "tenant": r.get("tenant"),
                "cve": r.get("cve_id"),
                "severity": r.get("severity"),
                "hostname": r.get("hostname")
            }
        }
        #print(f"from enricher {name}")
        return endpoints.get(name)
