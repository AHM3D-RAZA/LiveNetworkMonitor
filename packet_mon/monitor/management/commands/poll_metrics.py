import requests
from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.core.mail import send_mail
from django.utils import timezone
from django.conf import settings
from monitor.models import Device, Metrics
from monitor.snmp_utils import get_metrics
from uuid import UUID

GNS3_URL   = 'http://127.0.0.1:3080/v2'
PROJECT_ID = settings.GNS_PROJECT_ID

CPU_ALERT_THRESHOLD = getattr(settings, 'CPU_THRESHOLD', 80)
MEM_ALERT_THRESHOLD = getattr(settings, 'MEMORY_THRESHOLD', 80)
ALERT_RECIPIENTS    = getattr(settings, 'ALERT_RECIPIENTS', [settings.EMAIL_HOST_USER])

class Command(BaseCommand):
    help = 'Sync topology, poll metrics, and send alerts on status or thresholds'

    def handle(self, *args, **options):
        # ─── 1) Snapshot old statuses BEFORE any sync ───
        old_statuses = {
            dev.gns3_node_id: dev.status
            for dev in Device.objects.exclude(gns3_node_id__isnull=True)
        }
        print('old status of all devices', old_statuses)

        # ─── 2) Sync topology so DB.status = GNS3 status ───
        try:
            call_command('sync_gns3')
            self.stdout.write("[poll] Ran sync_gns3")
        except Exception as e:
            self.stderr.write(f"[poll] sync_gns3 FAILED: {e}")

        # ─── 3) Fetch nodes from GNS3 ───
        try:
            resp = requests.get(f'{GNS3_URL}/projects/{PROJECT_ID}/nodes')
            resp.raise_for_status()
            nodes = resp.json()
        except Exception as e:
            self.stderr.write(f"[poll] ERROR fetching nodes: {e}")
            return

        # ─── 4) Process each node ───
        for node in nodes:
            node_id = node.get('node_id')
            name    = node.get('name', '<unknown>')
            dev     = Device.objects.filter(gns3_node_id=node_id).first()

            if not dev or not dev.ip_address:
                self.stdout.write(f"[poll] Skipping {name}: no IP")
                continue

            # ─── 5) Determine new status ───
            raw = str(node.get('status','')).lower()
            new_status = 'online' if raw != 'stopped' else 'offline'

            # ─── 6) Compare old→new and alert on offline transition ───
            # prev = old_statuses.get(node_id)
            try:
                prev = old_statuses.get(UUID(node_id))
            except Exception:
                prev = None

            print(f'previous status: {prev} new status:_{new_status}')
            if prev == 'online' and new_status == 'offline':
                self.stdout.write(f"[DEBUG] {dev.name} went offline")
                subj = f"ALERT: {dev.name} OFFLINE"
                body = f"{dev.name} ({dev.ip_address}) went offline at {timezone.now().isoformat()}."
                try:
                    send_mail(subj, body,
                              settings.EMAIL_HOST_USER,
                              ALERT_RECIPIENTS, fail_silently=False)
                    self.stdout.write(f"[alert] Offline mail sent for {dev.name}")
                except Exception as e:
                    self.stderr.write(f"[alert] Failed offline mail: {e}")

            # ─── 7) Update the DB status and timestamp ───
            dev.status       = new_status
            dev.last_checked = timezone.now()
            dev.save(update_fields=['status','last_checked'])

            # ─── 8) Poll SNMP/ping metrics ───
            try:
                m = get_metrics(dev.ip_address)
                new_metric = Metrics.objects.create(device=dev, **m)
            except Exception as e:
                self.stderr.write(f"[poll] ERROR polling {dev.name}: {e}")
                continue

            self.stdout.write(f"[DEBUG] {dev.name} CPU={m['cpu_usage']:.1f}%, MEM={m['memory_usage']:.1f}%")

            # ─── 9) CPU edge alert ───
            prev_cpu_list = Metrics.objects.filter(device=dev) \
                              .order_by('-timestamp') \
                              .values_list('cpu_usage', flat=True)[1:2]
            prev_cpu = prev_cpu_list[0] if prev_cpu_list else 0.0
            if prev_cpu <= CPU_ALERT_THRESHOLD < new_metric.cpu_usage:
                self.stdout.write(f"[DEBUG] CPU crossed {CPU_ALERT_THRESHOLD}%")
                try:
                    send_mail(
                        subject=f"[ALERT] {dev.name} CPU {new_metric.cpu_usage:.1f}%",
                        message=f"CPU usage crossed {CPU_ALERT_THRESHOLD}%: now {new_metric.cpu_usage:.1f}%",
                        from_email=settings.EMAIL_HOST_USER,
                        recipient_list=ALERT_RECIPIENTS,
                        fail_silently=False
                    )
                    self.stdout.write(f"[alert] CPU mail sent for {dev.name}")
                except Exception as e:
                    self.stderr.write(f"[alert] Failed CPU mail: {e}")

            # ─── 10) Memory edge alert ───
            prev_mem_list = Metrics.objects.filter(device=dev) \
                              .order_by('-timestamp') \
                              .values_list('memory_usage', flat=True)[1:2]
            prev_mem = prev_mem_list[0] if prev_mem_list else 0.0
            if prev_mem <= MEM_ALERT_THRESHOLD < new_metric.memory_usage:
                self.stdout.write(f"[DEBUG] MEM crossed {MEM_ALERT_THRESHOLD}%")
                try:
                    send_mail(
                        subject=f"[ALERT] {dev.name} MEM {new_metric.memory_usage:.1f}%",
                        message=f"Memory usage crossed {MEM_ALERT_THRESHOLD}%: now {new_metric.memory_usage:.1f}%",
                        from_email=settings.EMAIL_HOST_USER,
                        recipient_list=ALERT_RECIPIENTS,
                        fail_silently=False
                    )
                    self.stdout.write(f"[alert] MEM mail sent for {dev.name}")
                except Exception as e:
                    self.stderr.write(f"[alert] Failed MEM mail: {e}")

            # ─── 11) Final log ───
            self.stdout.write(
                f"[poll] {dev.name}: status={dev.status}, "
                f"cpu={m['cpu_usage']:.1f}%, mem={m['memory_usage']:.1f}%, "
                f"lat={m['ping_latency']:.1f}ms, bw={m['bandwidth']:.1f}Mbps"
            )