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
import threading
import webbrowser

PORT = 63210

def get_resource_dir():
    """Locate directory containing index.html (supports PyInstaller onefile bundle)."""
    if getattr(sys, 'frozen', False):
        # 1. Prefer external index.html if user placed one next to the executable
        exe_dir = os.path.dirname(sys.executable)
        if os.path.isfile(os.path.join(exe_dir, 'index.html')):
            return exe_dir
        # 2. Bundled assets in PyInstaller extraction temp dir
        if hasattr(sys, '_MEIPASS'):
            return sys._MEIPASS
    return os.path.dirname(os.path.abspath(__file__))

def free_stale_port(port):
    """Cleanly terminate any orphaned process occupying the target port on Windows."""
    if sys.platform != 'win32':
        return
    try:
        output = subprocess.check_output(
            f'netstat -aon | findstr ":{port} "',
            shell=True,
            text=True,
            stderr=subprocess.DEVNULL
        )
        current_pid = os.getpid()
        for line in output.splitlines():
            parts = line.strip().split()
            if len(parts) >= 5 and f':{port}' in parts[1]:
                try:
                    pid = int(parts[-1])
                    if pid != 0 and pid != current_pid:
                        subprocess.run(['taskkill', '/F', '/PID', str(pid)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                        time.sleep(0.3)
                except Exception:
                    pass
    except Exception:
        pass

def open_browser(url, delay=0.8):
    """Launch default browser in a background thread."""
    def _open():
        time.sleep(delay)
        try:
            webbrowser.open(url)
        except Exception:
            pass
    t = threading.Thread(target=_open, daemon=True)
    t.start()

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

    def __init__(self, *args, directory=None, **kwargs):
        if directory is None:
            directory = get_resource_dir()
        super().__init__(*args, directory=directory, **kwargs)

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
    resource_dir = get_resource_dir()
    os.chdir(resource_dir)

    free_stale_port(PORT)

    local_ip = get_local_ip()
    subnet = f"{'.'.join(local_ip.split('.')[:3])}.0/24"
    url = f"http://localhost:{PORT}"

    print("=" * 66)
    print("      LAN RADAR - LOCAL NETWORK IP & TOPOLOGY SCANNER")
    print("=" * 66)
    print(f"[*] Detected Local Machine IP : {local_ip}")
    print(f"[*] Local Subnet              : {subnet}")
    print(f"[*] Web Server Address        : {url}")
    print(f"[*] Serving Directory         : {resource_dir}")
    print("=" * 66)
    print("[*] Launching browser automatically...")
    print("[*] Keep this window open while using the scanner.")
    print("[*] Press Ctrl+C in this window to stop the server.")
    print("=" * 66)
    sys.stdout.flush()

    open_browser(url)

    socketserver.TCPServer.allow_reuse_address = True
    try:
        httpd = socketserver.TCPServer(('0.0.0.0', PORT), LocalScannerHTTPHandler)
    except OSError as e:
        print(f"[!] Warning: Port {PORT} busy ({e}). Attempting fallback port...")
        httpd = socketserver.TCPServer(('0.0.0.0', 0), LocalScannerHTTPHandler)
        alt_port = httpd.server_address[1]
        url = f"http://localhost:{alt_port}"
        print(f"[*] Switched to alternate URL: {url}")
        open_browser(url, delay=0.2)

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[*] Server shutdown requested by user. Exiting...")
    finally:
        httpd.server_close()

if __name__ == '__main__':
    run_server()
