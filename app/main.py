from fastapi import Depends, FastAPI, HTTPException
import psutil
from concurrent.futures import ThreadPoolExecutor
import concurrent.futures
import subprocess
import app.auth as auth
import socket
import ipaddress
import logging

app = FastAPI(dependencies=[Depends(auth.verify_api_key)], docs_url=None, redoc_url=None, openapi_url=None)
logger = logging.getLogger(__name__)

def find_hosts():
    cmd = psutil.net_if_addrs()
    ip_list = []
    for interface in cmd:
        for address in cmd[interface]:
            if address.family == socket.AF_INET:
                if address.netmask == '255.255.255.255':
                    continue
                if address.address.startswith('127.'):
                    continue
                ipmask = (address.address) + ('/') + (address.netmask)
                ips = ipaddress.IPv4Interface(ipmask)
                if ips.network.prefixlen < 24:
                    continue
                for ip in ips.network.hosts():
                    ip_list.append(ip)
    return ip_list    

def ping():
    hosts = find_hosts()
    ip_list = []
    future_to_ip = {}
    with ThreadPoolExecutor(max_workers=128) as executor:
        for host in hosts:    
            func = subprocess.run
            cmd = ['ping', '-c', '1','-W', '1', str(host)]
            future = executor.submit(func, cmd, stdout = subprocess.DEVNULL, stderr = subprocess.DEVNULL)
            future_to_ip[future] = str(host)
        for future in concurrent.futures.as_completed(future_to_ip):
            rs = future.result()
            if rs.returncode == 0:
                ip_list.append(future_to_ip[future])
    return(ip_list)    

@app.get("/")
def read_root():
    return{"Hello": "World"}

@app.get("/system/cpu")
def read_cpu():
    return{"cpu_percent": psutil.cpu_percent(interval=0.5), "cpu_cores": psutil.cpu_count(True)}

@app.get("/system/ram")
def read_ram():
    return{"virtual memory": psutil.virtual_memory()}

@app.get("/system/disk")
def read_disk():
    return{"disk": psutil.disk_usage('/')}

@app.get("/system/network/devices")
def read_network():
    return{"devices": ping()}

@app.post('/system/shutdown')
def shutdown_system():
    try:
        subprocess.run(['systemctl', 'poweroff'], check=True)
        return 'Desligamento solicitado'
    except FileNotFoundError:
        logger.exception('systemctl não encontrado')
        raise HTTPException(500, 'Erro ao desligar')
    except subprocess.CalledProcessError as e:
        logger.exception(f'systemctl falhou {e.returncode}')
        raise HTTPException(500, 'Erro ao desligar')

@app.get('/system/processes')
def get_processes():
    processes = []
    for proc in psutil.process_iter(['pid','name','username']):
        processes.append(proc.info)

    return {'processes': processes}
