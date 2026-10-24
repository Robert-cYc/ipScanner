import http.server
import socket
import socketserver
import json
import os
import sys
import subprocess
import concurrent.futures
import re
import time
import urllib.parse

PORT = 63210

def get_local_ip():
    """Detect the active local LAN IPv4 address via outbound route inspection."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
    except Exception:
        try:
            ip = socket.gethostbyname(socket.gethostname())
        except Exception:
            ip = '127.0.0.1'
    finally:
        s.close()
    return ip

def get_arp_devices(subnet_filter=None):
    """Retrieve all dynamic devices from the OS ARP cache table."""
    devices = {}
    try:
        output = subprocess.check_output(['arp', '-a'], text=True, stderr=subprocess.DEVNULL)
        for line in output.splitlines():
            m = re.search(r'(\d+\.\d+\.\d+\.\d+)\s+([0-9a-fA-F-]+)\s+(\w+)', line)
            if m:
                ip, mac, typ = m.groups()
                if typ.lower() == 'dynamic' and not ip.endswith('.255'):
                    if subnet_filter is None or ip.startswith(subnet_filter + '.'):
                        devices[ip] = mac.upper()
    except Exception:
        pass
    return devices

def ping_host(ip, timeout_ms=300):
    """Ping a single host using Windows native ICMP ping."""
    cmd = ['ping', '-n', '1', '-w', str(timeout_ms), ip]
    t0 = time.time()
    res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    rtt = max(1, int((time.time() - t0) * 1000))
    return ip, res.returncode == 0, rtt

def scan_subnet(subnet_base):
    """Perform a rapid multi-threaded ICMP ping & ARP table sweep across /24."""
    active_map = {}

    # 1. Inspect existing ARP cache
    arp_devs = get_arp_devices(subnet_base)
    for ip, mac in arp_devs.items():
        try:
            h = int(ip.split('.')[-1])
        except Exception:
            h = 0
        active_map[ip] = {
            'ip': ip,
            'host': h,
            'mac': mac,
            'rtt': 2,
            'reason': 'ARP Cache Active'
        }

    # 2. Multi-threaded ICMP ping sweep (60 parallel threads)
    def worker(i):
        target_ip = f"{subnet_base}.{i}"
        _, is_up, rtt = ping_host(target_ip, timeout_ms=300)
        return target_ip, i, is_up, rtt

    with concurrent.futures.ThreadPoolExecutor(max_workers=60) as executor:
        futures = [executor.submit(worker, i) for i in range(1, 255)]
        for f in concurrent.futures.as_completed(futures):
            target_ip, host_num, is_up, rtt = f.result()
            if is_up:
                mac = arp_devs.get(target_ip, '')
                active_map[target_ip] = {
                    'ip': target_ip,
                    'host': host_num,
                    'mac': mac,
                    'rtt': rtt,
                    'reason': 'ICMP Echo Reply'
                }

    # 3. Post-ping ARP table harvest (ping sweep populates kernel ARP cache)
    fresh_arp = get_arp_devices(subnet_base)
    for ip, mac in fresh_arp.items():
        if ip in active_map:
            if not active_map[ip]['mac']:
                active_map[ip]['mac'] = mac
        else:
            try:
                h = int(ip.split('.')[-1])
            except Exception:
                h = 0
            active_map[ip] = {
                'ip': ip,
                'host': h,
                'mac': mac,
                'rtt': 2,
                'reason': 'ARP Discovered'
            }

    sorted_devs = sorted(list(active_map.values()), key=lambda x: x['host'])
    return sorted_devs

class LocalScannerHTTPHandler(http.server.SimpleHTTPRequestHandler):
    """Static file handler extended with network discovery telemetry endpoint."""

    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate')
        super().end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        query = urllib.parse.parse_qs(parsed.query)

        if parsed.path == '/api/my-ip':
            local_ip = get_local_ip()
            parts = local_ip.split('.')
            subnet = '.'.join(parts[:3]) if len(parts) == 4 else '192.168.1'
            host_num = int(parts[3]) if len(parts) == 4 else 1

            payload = {
                'ip': local_ip,
                'subnet': subnet,
                'host': host_num,
                'hostname': socket.gethostname()
            }
            self.send_json(payload)
            return

        elif parsed.path == '/api/arp-devices':
            subnet = query.get('subnet', [None])[0]
            devs = get_arp_devices(subnet)
            self.send_json({'devices': devs})
            return

        elif parsed.path == '/api/scan-subnet':
            subnet = query.get('subnet', ['192.168.0'])[0]
            devs = scan_subnet(subnet)
            self.send_json({'subnet': subnet, 'count': len(devs), 'devices': devs})
            return

        return super().do_GET()

    def send_json(self, payload):
        data = json.dumps(payload).encode('utf-8')
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)

def run_server():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)

    local_ip = get_local_ip()
    print("=" * 60)
    print("      LOCAL NETWORK IP SCANNER - BACKEND SERVER")
    print("=" * 60)
    print(f"[*] Detected Local Machine IP: {local_ip}")
    print(f"[*] Subnet: {'.'.join(local_ip.split('.')[:3])}.0/24")
    print(f"[*] Web Server URL: http://localhost:{PORT}")
    print("=" * 60)
    sys.stdout.flush()

    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(('0.0.0.0', PORT), LocalScannerHTTPHandler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down server.")

if __name__ == '__main__':
    run_server()
