from fastmcp import FastMCP
import docker
import os

# Initialize FastMCP Server
mcp = FastMCP("UniversalSandbox")
client = docker.from_env()

@mcp.tool()
def execute_python(code: str, timeout: int = 30):
    """
    Executes Python code in a secure, isolated Docker container.
    Returns the stdout/stderr of the execution.
    """
    try:
        container = client.containers.run(
            "python:3.12-slim",
            command=f"python3 -c \"{code}\"",
            remove=True,
            network_disabled=True,
            mem_limit="512m",
            stderr=True,
            stdout=True
        )
        return container.decode("utf-8")
    except Exception as e:
        return f"Execution Error: {str(e)}"

if __name__ == "__main__":
    mcp.run()
