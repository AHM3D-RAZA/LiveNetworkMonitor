import requests
from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone
from monitor.models import Device

GNS3_URL   = 'http://127.0.0.1:3080/v2'
PROJECT_ID = settings.GNS_PROJECT_ID  # e.g. '0cfc7a2c-815a-4a6e-aa01-ee62f09c93df'

class Command(BaseCommand):
    help = 'Sync GNS3 nodes into the Device table'

    def handle(self, *args, **options):
        self.stdout.write("[sync_gns3] Starting sync…")

        try:
            resp = requests.get(f"{GNS3_URL}/projects/{PROJECT_ID}/nodes")
            resp.raise_for_status()
            nodes = resp.json()
        except Exception as e:
            self.stderr.write(f"[sync_gns3] ERROR fetching nodes: {e}")
            return

        ALLOWED_TYPES = {'dynamips', 'qemu', 'ethernet_switch'}

        for node in nodes:
            node_type = node.get('node_type') or node.get('type', '')
            if node_type not in ALLOWED_TYPES:
                self.stdout.write(f"[sync_gns3] Skipping {node.get('name')} (type={node_type})")
                continue

            node_id      = node['node_id']
            name         = node.get('name', f"unnamed-{node_id}")
            status_flag  = node.get('status', 'stopped')
            last_checked = timezone.now()

            # Auto-discover management IP if GNS3 adapter marked
            ip = None
            for adapter in node.get('adapters', []):
                if adapter.get('management') and adapter.get('ip_address'):
                    ip = adapter['ip_address']
                    break

            defaults = {
                'name':             name,
                'status':           'online' if status_flag == 'started' else 'offline',
                'last_checked':     last_checked,
                'gns3_project_id':  PROJECT_ID,
            }
            if ip:
                defaults['ip_address'] = ip

            device, created = Device.objects.update_or_create(
                gns3_node_id=node_id,
                defaults=defaults
            )

            verb = "Created" if created else "Updated"
            self.stdout.write(
                f"[sync_gns3] {verb} {name} "
                f"(type={node_type}) IP={device.ip_address or '—'} "
                f"status={device.status}"
            )

        self.stdout.write("[sync_gns3] Sync complete.")
