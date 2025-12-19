"""
Claude Remote Executor Client
==============================
This module allows Claude to connect to a remote Colab instance
for executing code that exceeds local runtime limits.

Usage:
    from remote_executor import RemoteExecutor
    
    # Initialize with your ngrok URL
    executor = RemoteExecutor("https://xxxx-xx-xx-xxx-xx.ngrok-free.app")
    
    # Execute Python code
    result = executor.execute("print('Hello from Colab!')")
    
    # Run bash commands
    result = executor.bash("ls -la /content")
    
    # Download large files
    result = executor.download("https://example.com/large-file.zip")
    
    # Check disk space
    disk = executor.disk()
"""

import httpx
from typing import Optional, Dict, Any

class RemoteExecutor:
    """Client for connecting to Claude Remote Executor on Google Colab"""
    
    def __init__(self, base_url: str, timeout: int = 300):
        """
        Initialize the remote executor client.
        
        Args:
            base_url: The ngrok public URL (e.g., "https://xxxx.ngrok-free.app")
            timeout: Default timeout in seconds for requests
        """
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.client = httpx.Client(timeout=timeout)
        
    def _request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make a request to the remote executor"""
        url = f"{self.base_url}{endpoint}"
        try:
            response = self.client.request(method, url, **kwargs)
            return response.json()
        except httpx.TimeoutException:
            return {"success": False, "error": "Request timed out"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def health(self) -> Dict[str, Any]:
        """Check if the remote executor is online and get system stats"""
        return self._request("GET", "/health")
    
    def execute(self, code: str, timeout: Optional[int] = None) -> Dict[str, Any]:
        """
        Execute Python code on the remote Colab instance.
        
        Args:
            code: Python code to execute
            timeout: Optional timeout override in seconds
            
        Returns:
            Dict with keys: success, stdout, stderr, result, error
        """
        payload = {"code": code}
        if timeout:
            payload["timeout"] = timeout
        return self._request("POST", "/execute", json=payload)
    
    def bash(self, command: str, timeout: Optional[int] = None) -> Dict[str, Any]:
        """
        Execute a bash command on the remote Colab instance.
        
        Args:
            command: Bash command to execute
            timeout: Optional timeout override in seconds
            
        Returns:
            Dict with keys: success, returncode, stdout, stderr
        """
        payload = {"command": command}
        if timeout:
            payload["timeout"] = timeout
        return self._request("POST", "/bash", json=payload)
    
    def download(self, url: str, destination: str = "/content/downloads", 
                 filename: Optional[str] = None) -> Dict[str, Any]:
        """
        Download a file from URL to the remote Colab instance.
        
        Args:
            url: URL to download from
            destination: Directory to save the file
            filename: Optional filename (auto-detected from URL if not provided)
            
        Returns:
            Dict with keys: success, filepath, size_mb
        """
        payload = {
            "url": url,
            "destination": destination
        }
        if filename:
            payload["filename"] = filename
        return self._request("POST", "/download", json=payload)
    
    def ls(self, path: str = "/content") -> Dict[str, Any]:
        """
        List directory contents on the remote Colab instance.
        
        Args:
            path: Directory path to list
            
        Returns:
            Dict with keys: success, path, items (list of files/dirs)
        """
        return self._request("GET", "/ls", params={"path": path})
    
    def disk(self) -> Dict[str, Any]:
        """
        Get disk usage information from the remote Colab instance.
        
        Returns:
            Dict with keys: total_gb, used_gb, free_gb, percent_used
        """
        return self._request("GET", "/disk")
    
    def info(self) -> Dict[str, Any]:
        """Get server info and available endpoints"""
        return self._request("GET", "/")


def test_connection(base_url: str) -> bool:
    """Test if the remote executor is reachable"""
    executor = RemoteExecutor(base_url)
    result = executor.health()
    if result.get("status") == "healthy":
        print(f"✓ Connected to remote executor")
        print(f"  CPU: {result.get('cpu_percent')}%")
        print(f"  Memory: {result.get('memory_percent')}%")
        print(f"  Disk Free: {result.get('disk_free_gb')} GB")
        return True
    else:
        print(f"✗ Connection failed: {result.get('error', 'Unknown error')}")
        return False


# Example usage when run directly
if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        url = sys.argv[1]
        test_connection(url)
    else:
        print("Usage: python remote_executor.py <ngrok_url>")
