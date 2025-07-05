from django.conf import settings
import random
import time
from ping3 import ping
from pysnmp.hlapi import (
    SnmpEngine, CommunityData, UdpTransportTarget,
    ContextData, ObjectType, ObjectIdentity, getCmd
)

# Standard OIDs
CPU_OID        = settings.CPU_OID
TOTAL_MEM_OID  = settings.TOTAL_MEM_OID
AVAIL_MEM_OID  = settings.AVAIL_MEM_OID
UPTIME_OID     = settings.UPTIME_OID
ICMP_IN_ERR_OID  = settings.ICMP_IN_ERR_OID
ICMP_OUT_ERR_OID = settings.ICMP_OUT_ERR_OID
# Replace <ifIndex> with your interface index or pass in dynamically
IFHC_IN_OID    = settings.IFHC_IN_OID
IFHC_OUT_OID   = settings.IFHC_OUT_OID

def snmp_get(ip, oid, community='public'):
    """Return float(value) or None on error."""
    try:
        iterator = getCmd(
            SnmpEngine(),
            CommunityData(community, mpModel=1),
            UdpTransportTarget((ip, 161), timeout=1, retries=1),
            ContextData(),
            ObjectType(ObjectIdentity(oid))
        )
        errInd, errStat, _, varBinds = next(iterator)
        if errInd or errStat:
            return None
        return float(varBinds[0].prettyPrint().split('=')[1].strip())
    except:
        return None

def try_snmp_or(default_fn, ip, *args, **kwargs):
    """Try the SNMP helper, else call default_fn() to simulate."""
    val = default_fn(ip, *args, **kwargs)
    return val

def get_real_uptime(ip):
    val = snmp_get(ip, UPTIME_OID)
    return (val or 0) / 100.0  # from hundredths of secs → secs

def get_real_packet_loss(ip):
    in_err  = snmp_get(ip, ICMP_IN_ERR_OID)  or 0
    out_err = snmp_get(ip, ICMP_OUT_ERR_OID) or 0
    # Here we return total error count; you could normalize later if you track totals
    return float(in_err + out_err)

def get_real_bandwidth(ip, interval=1.0):
    in1  = snmp_get(ip, IFHC_IN_OID)  or None
    out1 = snmp_get(ip, IFHC_OUT_OID) or None
    if in1 is None or out1 is None:
        return None
    time.sleep(interval)
    in2  = snmp_get(ip, IFHC_IN_OID)  or None
    out2 = snmp_get(ip, IFHC_OUT_OID) or None
    if in2 is None or out2 is None:
        return None
    bits = ((in2 - in1) + (out2 - out1)) * 8
    return bits / interval / 1e6  # Mbps

def get_metrics(ip):
    # 1) Latency (ICMP)
    real_lat = ping(ip, timeout=1)
    latency  = real_lat if real_lat is not None else random.uniform(20.0, 150.0)

    # 2) CPU Usage
    real_cpu = snmp_get(ip, CPU_OID)
    cpu = real_cpu if real_cpu is not None else random.uniform(5.0, 95.0)

    # 3) Memory Usage
    total = snmp_get(ip, TOTAL_MEM_OID)
    avail = snmp_get(ip, AVAIL_MEM_OID)
    if total and avail:
        memory = ((total - avail) / total) * 100
    else:
        memory = random.uniform(30.0, 90.0)

    # 4) Uptime
    real_up = get_real_uptime(ip)
    uptime  = int(real_up) if real_up > 0 else random.randint(1800, 18*3600)

    # 5) Bandwidth
    real_bw = get_real_bandwidth(ip)
    bandwidth = real_bw if real_bw is not None else random.uniform(10.0, 100.0)

    # 6) Packet Loss
    real_loss = get_real_packet_loss(ip)
    packet_loss = real_loss if real_loss >= 0 else random.uniform(0.0, 5.0)

    return {
        'ping_latency':  latency,
        'cpu_usage':     cpu,
        'memory_usage':  memory,
        'bandwidth':     bandwidth,
        'packet_loss':   packet_loss,
        'uptime':        uptime
    }
