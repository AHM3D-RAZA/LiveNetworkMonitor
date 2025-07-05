from django.shortcuts import render
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http  import require_POST, require_http_methods
from django.core.mail import send_mail
from django.utils import timezone
from django.conf import settings
from django.db.models import OuterRef, Subquery, Avg, Count
import json, csv
from datetime import timedelta
from .models import Device, Metrics, Log
from .snmp_utils import get_metrics as fetch_snmp_metrics


def dashboard_view(request):
    # Renders a simple table of devices
    devices = Device.objects.all()
    return render(request, 'monitor/dashboard.html', {'devices': devices})

def get_devices(request):
    devices = Device.objects.annotate(
        latest_cpu=Subquery(
            Metrics.objects.filter(device=OuterRef('pk'))
            .order_by('-timestamp')
            .values('cpu_usage')[:1]
        ),
        latest_memory=Subquery(
            Metrics.objects.filter(device=OuterRef('pk'))
            .order_by('-timestamp')
            .values('memory_usage')[:1]
        ),
        latest_bandwidth=Subquery(
            Metrics.objects.filter(device=OuterRef('pk'))
            .order_by('-timestamp')
            .values('bandwidth')[:1]
        ),
        latest_ping=Subquery(
            Metrics.objects.filter(device=OuterRef('pk'))
            .order_by('-timestamp')
            .values('ping_latency')[:1]
        ),
        latest_uptime=Subquery(
            Metrics.objects.filter(device=OuterRef('pk'))
            .order_by('-timestamp')
            .values('uptime')[:1]
        )
    )
    
    data = [
        {
            'id': d.id,
            'name': d.name,
            'ip_address': d.ip_address,
            'status': d.status,
            'cpu': d.latest_cpu,
            'memory': d.latest_memory,
            'bandwidth': d.latest_bandwidth,
            'ping': d.latest_ping,
            'uptime': d.latest_uptime,
            'last_checked': d.last_checked.isoformat() if d.last_checked else None
        }
        for d in devices
    ]
    return JsonResponse({'devices': data})

def get_metrics(request, device_id):
    qs = Metrics.objects.filter(device_id=device_id).order_by('-timestamp')[:50]
    data = [{
        'timestamp': m.timestamp,
        'cpu': m.cpu_usage,
        'mem': m.memory_usage,
        'ping': m.ping_latency
    } for m in reversed(qs)]
    return JsonResponse({'metrics': data})

def export_metrics_csv(request, device_id):
    qs = Metrics.objects.filter(device_id=device_id).order_by('timestamp')
    resp = HttpResponse(content_type='text/csv')
    resp['Content-Disposition'] = f'attachment; filename="device_{device_id}_metrics.csv"'
    writer = csv.writer(resp)
    writer.writerow(['timestamp','cpu','mem','ping'])
    for m in qs:
        writer.writerow([m.timestamp, m.cpu_usage, m.memory_usage, m.ping_latency])
    return resp

@csrf_exempt
def update_status(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST only'}, status=400)

    try:
        payload = json.loads(request.body)
    except ValueError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    for dev in payload.get('devices', []):
        # Try ID first, then fallback to IP
        device = None
        if 'id' in dev:
            device = Device.objects.filter(pk=dev['id']).first()
        else:
            ip = dev.get('ip_address')
            if ip:
                device = Device.objects.filter(ip_address=ip).first()

        if not device:
            # we skip unknown devices rather than create new ones
            continue

        old_status = device.status
        device.status = dev.get('status', device.status)
        device.last_checked = timezone.now()
        device.save(update_fields=['status','last_checked'])

        # Create log entry
        Log.objects.create(
            user=None,
            device=device,
            action=f"Status → {device.status}",
            severity='critical' if device.status == 'offline' else 'info',
            source='system'
        )

        # Email alert on offline
        if old_status == 'online' and device.status == 'offline':
            send_mail(
                subject=f"ALERT: {device.name} went offline",
                message=f"{device.name} ({device.ip_address}) offline at {device.last_checked}.",
                from_email=settings.EMAIL_HOST_USER,
                recipient_list=[settings.EMAIL_HOST_USER],
                fail_silently=True,
            )

        # Fetch & save metrics
        metrics = fetch_snmp_metrics(device.ip_address)
        new_metric = Metrics.objects.create(device=device, **metrics)

        cpu_over = new_metric.cpu_usage > 80
        if cpu_over:
            has_previous_cpu = Metrics.objects.filter(
                device=device,
                cpu_usage__gt=80
            ).exclude(id=new_metric.id).exists()
            if not has_previous_cpu:
                Log.objects.create(
                    device=device,
                    action=f"CPU usage exceeded 80%: {new_metric.cpu_usage}%",
                    severity='warning',
                    source='device'
                )

        mem_over = new_metric.memory_usage > 80
        if mem_over:
            has_previous_mem = Metrics.objects.filter(
                device=device,
                memory_usage__gt=80
            ).exclude(id=new_metric.id).exists()
            if not has_previous_mem:
                Log.objects.create(
                    device=device,
                    action=f"Memory usage exceeded 80%: {new_metric.memory_usage}%",
                    severity='warning',
                    source='device'
                )

        # Example threshold alert
        if metrics.get('cpu_usage', 0) > getattr(settings, 'CPU_THRESHOLD', 90):
            send_mail(
                subject=f"[ALERT] {device.name} CPU {metrics['cpu_usage']}%",
                message="CPU exceeded threshold.",
                from_email=settings.EMAIL_HOST_USER,
                recipient_list=[settings.EMAIL_HOST_USER],
                fail_silently=True,
            )


    return JsonResponse({'status': 'ok'})



@csrf_exempt
@require_POST
def add_device(request):
    """
    Expects JSON { "name": "...", "ip_address": "..." }.
    Creates a Device with default status='online' and last_checked=now().
    """
    data = json.loads(request.body)
    dev = Device.objects.create(
        name=data['name'],
        ip_address=data['ip_address'],
        status='online',                    # default
        last_checked=timezone.now()         # now
    )
    return JsonResponse({
        'id':           dev.id,
        'name':         dev.name,
        'ip_address':   dev.ip_address,
        'status':       dev.status,
        'last_checked': dev.last_checked.isoformat()
    }, status=201)


@csrf_exempt
def delete_device(request, device_id):
    if request.method == 'DELETE':
        Device.objects.filter(id=device_id).delete()
        return JsonResponse({'status': 'success'})
    return JsonResponse({'error': 'Invalid method'}, status=400)

def logs_view(request):
    logs = Log.objects.all().select_related('device', 'user')
    return render(request, 'monitor/view_log.html', {'logs': logs})

def metrics_report_view(request):
    return render(request, 'monitor/reports.html')



@csrf_exempt
@require_http_methods(["GET", "PUT", "DELETE"])
def device_detail(request, device_id):
    """
    GET    -> fetch a single device’s data for the edit modal
    PUT    -> update name/ip
    DELETE -> remove it
    """
    try:
        device = Device.objects.get(id=device_id)
    except Device.DoesNotExist:
        return JsonResponse({'error': 'Device not found'}, status=404)

    if request.method == 'GET':
        # return JSON for the edit modal
        return JsonResponse({
            'id':         device.id,
            'name':       device.name,
            'ip_address': device.ip_address,
            'status':     device.status,
            # add other fields if needed
        })

    elif request.method == 'PUT':
        data = json.loads(request.body)
        device.name       = data.get('name', device.name)
        device.ip_address = data.get('ip_address', device.ip_address)
        device.save()
        return JsonResponse({'status': 'success'})

    elif request.method == 'DELETE':
        device.delete()
        return JsonResponse({'status': 'success'})

def reports_view(request):
    """Renders the reports.html template."""
    return render(request, 'monitor/reports.html')

def api_report_metrics(request):
    """
    Returns JSON:
      {
        labels: ['2025‑04‑29', … ],
        cpu:    [45.2, …],
        memory: [61.3, …],
        latency:[12.7, …]
      }
    for the past 7 days.
    """
    end   = timezone.now()
    start = end - timedelta(days=6)  # include today + past 6
    
    qs = (
      Metrics.objects
        .filter(timestamp__date__gte=start.date())
        .extra(select={'day':'date(timestamp)'})
        .values('day')
        .annotate(
          cpu_avg    = Avg('cpu_usage'),
          mem_avg    = Avg('memory_usage'),
          ping_avg   = Avg('ping_latency')
        )
        .order_by('day')
    )

    labels    = [r['day'] for r in qs]
    cpu_data  = [round(r['cpu_avg'] or 0, 1) for r in qs]
    mem_data  = [round(r['mem_avg'] or 0, 1) for r in qs]
    ping_data = [round(r['ping_avg'] or 0, 1) for r in qs]

    return JsonResponse({
      'labels': labels,
      'cpu':    cpu_data,
      'memory': mem_data,
      'latency': ping_data
    })

def api_report_alerts(request):
    """
    Returns JSON:
      {
        labels: ['Critical','Warning','Informational'],
        data:   [12, 34, 56]
      }
    for all Log entries in the past 7 days.
    """
    since = timezone.now() - timedelta(days=7)
    qs = (
      Log.objects
         .filter(timestamp__gte=since)
         .values('severity')
         .annotate(count=Count('id'))
    )
    # ensure the three categories always in order:
    severity_order = ['critical','warning','info']
    labels = []
    data   = []
    for sev in severity_order:
        rec = next((r for r in qs if r['severity']==sev), None)
        # Map 'critical' → 'Critical', 'warning' → 'Warning', etc.
        labels.append(Log.SEVERITY_CHOICES_DICT[sev])  # see note below
        data.append(rec['count'] if rec else 0)

    return JsonResponse({'labels': labels, 'data': data})

def view_log(request):
    return render(request, 'monitor/view_log.html')

def api_logs(request):
    qs = (
      Log.objects
         .select_related('device')
         .order_by('-timestamp')
    )
    data = [
      {
        'id':           L.id,
        'timestamp':    L.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
        'severity':     L.severity,
        'source':       L.source,
        'device':       L.device.name if L.device else '',
        'message':      L.action,
        'acknowledged': L.acknowledged
      }
      for L in qs
    ]
    return JsonResponse(data, safe=False)

@csrf_exempt
@require_POST
def api_clear_logs(request):
    Log.objects.all().delete()
    return JsonResponse({'status':'ok'})


@csrf_exempt
@require_POST
def api_toggle_ack(request, log_id):
    try:
        log = Log.objects.get(id=log_id)
        log.acknowledged = not log.acknowledged
        log.save()
        return JsonResponse({'status': 'success', 'acknowledged': log.acknowledged})
    except Log.DoesNotExist:
        return JsonResponse({'error': 'Log not found'}, status=404)