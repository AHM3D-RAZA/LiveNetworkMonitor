from django.db import models
from django.conf import settings

class Device(models.Model):
    name        = models.CharField(max_length=100)
    ip_address  = models.GenericIPAddressField(unique=True, null=True, blank=True)
    status      = models.CharField(
        max_length=10,
        choices=[('online','Online'),('offline','Offline'),('warning','Warning')],
        default='online'
    )
    last_checked = models.DateTimeField(null=True, blank=True)
    gns3_project_id  = models.UUIDField(null=True, blank=True)
    gns3_node_id     = models.UUIDField(null=True, blank=True)
    def __str__(self): return f"{self.name} ({self.ip_address})"

class Metrics(models.Model):
    device = models.ForeignKey(Device, on_delete=models.CASCADE)
    cpu_usage = models.FloatField(null=True, blank=True)
    memory_usage = models.FloatField(null=True, blank=True)
    bandwidth = models.FloatField(null=True, blank=True)
    ping_latency = models.FloatField(null=True, blank=True)
    packet_loss = models.FloatField(null=True, blank=True)
    uptime = models.IntegerField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

class User(models.Model):
    username = models.CharField(max_length=100, unique=True)
    password_hash = models.CharField(max_length=255)
    role = models.CharField(max_length=10, choices=[('admin', 'Admin'), ('viewer', 'Viewer')])

class Log(models.Model):
    SEVERITY_CHOICES = [
        ('critical','Critical'),
        ('warning','Warning'),
        ('info','Informational'),
    ]
    SEVERITY_CHOICES_DICT = dict(SEVERITY_CHOICES)
    SOURCE_CHOICES = [
        ('system','System'),
        ('network','Network'),
        ('device','Device'),
        ('security','Security'),
    ]

    user         = models.ForeignKey(settings.AUTH_USER_MODEL,
                                     on_delete=models.SET_NULL,
                                     null=True, blank=True)
    device       = models.ForeignKey('Device', on_delete=models.CASCADE, null=True)
    action       = models.CharField(max_length=200)
    severity     = models.CharField(max_length=10,
                                    choices=SEVERITY_CHOICES,
                                    default='info')
    source       = models.CharField(max_length=10,
                                    choices=SOURCE_CHOICES,
                                    default='system')
    timestamp    = models.DateTimeField(auto_now_add=True)
    acknowledged = models.BooleanField(default=False)

    def __str__(self):
        return f"[{self.get_severity_display()}] {self.action}"
