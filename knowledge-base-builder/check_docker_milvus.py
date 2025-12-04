#!/usr/bin/env python3
"""
Check Docker Milvus container and disk space issues.
"""
import sys
import subprocess
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from utils.logger import setup_logging, get_logger

setup_logging(log_level=None, console_output=True, file_output=False)
logger = get_logger(__name__)


def run_cmd(cmd, check=True):
    """Run a command and return output."""
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=10
        )
        if check and result.returncode != 0:
            return None, result.stderr
        return result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return None, "Command timed out"
    except Exception as e:
        return None, str(e)


def main():
    """Check Docker Milvus status."""
    print("=" * 60)
    print("Docker Milvus Diagnostic")
    print("=" * 60)
    
    # Check if Docker is available
    print("\n[1] Checking Docker availability...")
    docker_paths = [
        "/usr/local/bin/docker",
        "/Applications/Docker.app/Contents/Resources/bin/docker",
        "docker"  # Try in PATH
    ]
    
    docker_cmd = None
    for path in docker_paths:
        stdout, stderr = run_cmd(f"which {path}" if path != "docker" else "which docker", check=False)
        if stdout and stdout.strip():
            docker_cmd = path
            print(f"  ✓ Found Docker at: {docker_cmd}")
            break
    
    if not docker_cmd:
        print("  ✗ Docker not found in common locations")
        print("  Please ensure Docker Desktop is running")
        return
    
    # Check Docker daemon
    print("\n[2] Checking Docker daemon...")
    stdout, stderr = run_cmd(f"{docker_cmd} ps", check=False)
    if stdout:
        print("  ✓ Docker daemon is running")
    else:
        print(f"  ✗ Docker daemon not accessible: {stderr}")
        print("  Please start Docker Desktop")
        return
    
    # Find Milvus containers
    print("\n[3] Finding Milvus containers...")
    stdout, stderr = run_cmd(f'{docker_cmd} ps --filter "name=milvus" --format "{{{{.Names}}}}\t{{{{.Status}}}}\t{{{{.Ports}}}}"', check=False)
    if stdout and stdout.strip():
        print("  Milvus containers:")
        for line in stdout.strip().split('\n'):
            if line.strip():
                print(f"    {line}")
    else:
        print("  No Milvus containers found")
        print("  Searching for containers with 'milvus' in name...")
        stdout, stderr = run_cmd(f'{docker_cmd} ps --format "{{{{.Names}}}}\t{{{{.Status}}}}" | grep -i milvus', check=False)
        if stdout:
            print(stdout)
        else:
            print("  No Milvus containers running")
    
    # Check Docker disk usage
    print("\n[4] Docker disk usage...")
    stdout, stderr = run_cmd(f"{docker_cmd} system df", check=False)
    if stdout:
        print(stdout)
    else:
        print(f"  Cannot check: {stderr}")
    
    # Check Milvus volumes
    print("\n[5] Milvus volumes...")
    stdout, stderr = run_cmd(f'{docker_cmd} volume ls | grep -i milvus', check=False)
    if stdout and stdout.strip():
        print("  Milvus volumes:")
        print(stdout)
        
        # Get volume details
        volumes = [line.split()[1] for line in stdout.strip().split('\n') if line.strip() and not line.startswith('VOLUME')]
        for vol in volumes:
            print(f"\n  Volume {vol} details:")
            stdout2, stderr2 = run_cmd(f'{docker_cmd} volume inspect {vol}', check=False)
            if stdout2:
                print(f"    {stdout2[:200]}...")
    else:
        print("  No Milvus volumes found")
    
    # Check container disk space
    print("\n[6] Container disk space...")
    stdout, stderr = run_cmd(f'{docker_cmd} ps --filter "name=milvus" -q', check=False)
    if stdout and stdout.strip():
        container_id = stdout.strip().split('\n')[0]
        print(f"  Checking container {container_id}...")
        stdout2, stderr2 = run_cmd(f'{docker_cmd} exec {container_id} df -h', check=False)
        if stdout2:
            print(stdout2)
        else:
            print(f"  Cannot check: {stderr2}")
    
    # Recommendations
    print("\n" + "=" * 60)
    print("Recommendations:")
    print("=" * 60)
    print("If Docker disk space is low:")
    print("1. Clean up Docker system:")
    print(f"   {docker_cmd} system prune -a --volumes")
    print("\n2. Clean up unused images:")
    print(f"   {docker_cmd} image prune -a")
    print("\n3. Check Docker Desktop settings:")
    print("   - Open Docker Desktop")
    print("   - Go to Settings > Resources > Advanced")
    print("   - Check Disk image size and location")
    print("\n4. Restart Milvus container:")
    print(f"   {docker_cmd} restart <milvus_container_name>")


if __name__ == "__main__":
    main()

