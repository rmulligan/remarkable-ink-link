"""
Live integration test for the full InkLink workflow.

This test uses REAL services and will attempt to install and configure missing dependencies:
1. rmapi for reMarkable Cloud access
2. Neo4j for knowledge graph functionality
3. Required Python packages
4. API keys configuration

Run with:
poetry run pytest tests/test_live_roundtrip.py -v
"""

import os
import sys
import pytest
import logging
import tempfile
import shutil
import importlib.util
import asyncio
import subprocess
import platform
import json
import time
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple, Union

# Import core modules (early import to avoid E402 errors)
from inklink.services.qr_service import QRCodeService
from inklink.services.web_scraper_service import WebScraperService
from inklink.services.document_service import DocumentService
from inklink.services.pdf_service import PDFService
from inklink.services.remarkable_service import RemarkableService
from inklink.services.ai_service import AIService
from inklink.controllers.share_controller import ShareController
from inklink.controllers.ingest_controller import IngestController
from inklink.controllers.process_controller import ProcessController
from inklink.services.knowledge_graph_service import KnowledgeGraphService
from inklink.controllers.knowledge_graph_controller import KnowledgeGraphController

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("test_live_roundtrip")

# Constants
DEFAULT_NEO4J_VERSION = "5.14.0"
DEFAULT_RMAPI_VERSION = "0.0.24"

# Helper functions for dependency installation


def run_command(
    cmd: List[str],
    cwd: Optional[str] = None,
    env: Optional[Dict[str, str]] = None,
    log_cmd: bool = True,
    sensitive: bool = False,
) -> Tuple[int, str, str]:
    """
    Run a shell command and return exit code, stdout, and stderr.

    Args:
        cmd: Command and arguments as list
        cwd: Working directory (optional)
        env: Environment variables (optional)
        log_cmd: Whether to log the command (default: True)
        sensitive: Whether the command contains sensitive data like passwords (default: False)

    Returns:
        Tuple of (exit_code, stdout, stderr)
    """
    if log_cmd:
        if sensitive:
            # Just log the command name without arguments that might contain sensitive data
            logger.info(f"Running sensitive command: {cmd[0]}")
        else:
            logger.info(f"Running command: {' '.join(cmd)}")

    try:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=cwd,
            env=env or os.environ.copy(),
            text=True,
        )

        stdout, stderr = process.communicate()
        exit_code = process.returncode

        if exit_code != 0:
            logger.warning(f"Command exited with code {exit_code}")
            logger.warning(f"stderr: {stderr}")

        return exit_code, stdout, stderr
    except Exception as e:
        logger.error(f"Error executing command: {e}")
        return 1, "", str(e)


def ensure_python_package(package_name: str) -> bool:
    """
    Ensure a Python package is installed.

    Args:
        package_name: Name of the package

    Returns:
        True if installed successfully, False otherwise
    """
    # Check if already installed
    if importlib.util.find_spec(package_name):
        logger.info(f"Package {package_name} is already installed")
        return True

    logger.info(f"Installing Python package: {package_name}")

    # Try to install with poetry
    exit_code, stdout, stderr = run_command(["poetry", "add", package_name])

    if exit_code == 0:
        logger.info(f"Successfully installed {package_name} with poetry")

        # Force reload to ensure the package is available
        try:
            if package_name in sys.modules:
                importlib.reload(sys.modules[package_name])
            else:
                importlib.import_module(package_name)
            return True
        except ImportError:
            logger.error(f"Failed to load {package_name} after installation")
            return False

    # Try pip as fallback
    exit_code, stdout, stderr = run_command(
        [sys.executable, "-m", "pip", "install", package_name]
    )

    if exit_code == 0:
        logger.info(f"Successfully installed {package_name} with pip")

        # Force reload
        try:
            if package_name in sys.modules:
                importlib.reload(sys.modules[package_name])
            else:
                importlib.import_module(package_name)
            return True
        except ImportError:
            logger.error(f"Failed to load {package_name} after installation")
            return False

    logger.error(f"Failed to install {package_name}")
    return False


def ensure_rmapi(version: str = DEFAULT_RMAPI_VERSION) -> Tuple[bool, str]:
    """
    Ensure rmapi is installed.

    Args:
        version: Version to install (default: latest stable)

    Returns:
        Tuple of (success, path)
    """
    # Check if RMAPI_PATH is set and valid
    rmapi_path = os.environ.get("RMAPI_PATH")
    if rmapi_path and os.path.exists(rmapi_path) and os.access(rmapi_path, os.X_OK):
        logger.info(f"rmapi is already installed at {rmapi_path}")
        return True, rmapi_path

    # Determine installation directory
    install_dir = os.path.expanduser("~/.local/bin")
    os.makedirs(install_dir, exist_ok=True)

    # Determine system details
    system = platform.system().lower()
    machine = platform.machine().lower()

    # Map system and architecture to download URL format
    os_map = {"linux": "linux", "darwin": "darwin", "windows": "windows"}

    arch_map = {
        "x86_64": "amd64",
        "amd64": "amd64",
        "arm64": "arm64",
        "aarch64": "arm64",
    }

    # Get OS and architecture
    os_name = os_map.get(system)
    arch = arch_map.get(machine)

    if not os_name or not arch:
        logger.error(f"Unsupported system: {system} {machine}")
        return False, ""

    # Construct GitHub release URL
    base_url = f"https://github.com/juruen/rmapi/releases/download/v{version}"

    if system == "windows":
        filename = f"rmapi-{os_name}.exe"
    else:
        filename = f"rmapi-{os_name}-{arch}"

    download_url = f"{base_url}/{filename}"

    # Download rmapi
    logger.info(f"Downloading rmapi from {download_url}")

    import requests

    try:
        response = requests.get(download_url, stream=True)
        if response.status_code != 200:
            logger.error(f"Failed to download rmapi: {response.status_code}")
            return False, ""

        # Save to installation directory
        output_path = os.path.join(install_dir, "rmapi")
        with open(output_path, "wb") as f:
            f.write(response.content)

        # Make executable
        os.chmod(output_path, 0o755)

        logger.info(f"rmapi installed to {output_path}")

        # Set environment variable
        os.environ["RMAPI_PATH"] = output_path

        return True, output_path
    except Exception as e:
        logger.error(f"Error downloading rmapi: {e}")
        return False, ""


def ensure_neo4j(version: str = DEFAULT_NEO4J_VERSION) -> Tuple[bool, str]:
    """
    Ensure Neo4j is installed and running.

    Args:
        version: Version to install (default: latest stable)

    Returns:
        Tuple of (success, uri)
    """
    # Check if Neo4j package is installed
    neo4j_installed = importlib.util.find_spec("neo4j") is not None
    if not neo4j_installed:
        if not ensure_python_package("neo4j"):
            logger.error("Failed to install Neo4j Python package")
            return False, ""

    # Check if we're using Docker and Neo4j is already running
    neo4j_uri = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
    neo4j_username = os.environ.get("NEO4J_USERNAME", "neo4j")
    neo4j_password = os.environ.get("NEO4J_PASSWORD", "password")

    # Try to connect to existing Neo4j instance
    try:
        from neo4j import GraphDatabase

        driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_username, neo4j_password))

        with driver.session() as session:
            result = session.run("RETURN 1 as test")
            if result.single()["test"] == 1:
                logger.info(f"Connected to existing Neo4j instance at {neo4j_uri}")
                driver.close()
                return True, neo4j_uri
    except Exception as e:
        logger.warning(f"Could not connect to Neo4j at {neo4j_uri}: {e}")

    # Check if Docker is available
    exit_code, stdout, stderr = run_command(["docker", "--version"])
    if exit_code != 0:
        logger.error("Docker is not available, cannot start Neo4j")
        return False, ""

    # Start Neo4j with Docker
    container_name = "inklink_neo4j_test"

    # Check if container is already running
    exit_code, stdout, stderr = run_command(
        ["docker", "ps", "-q", "-f", f"name={container_name}"]
    )
    if stdout.strip():
        logger.info(f"Neo4j container {container_name} is already running")
    else:
        # Start container
        logger.info(f"Starting Neo4j container with Docker")
        # Set up command with potentially sensitive password information
        docker_cmd = [
            "docker",
            "run",
            "-d",
            "--name",
            container_name,
            "-p",
            "7474:7474",
            "-p",
            "7687:7687",
            "-e",
            f"NEO4J_AUTH={neo4j_username}/{neo4j_password}",
            f"neo4j:{version}",
        ]
        # Log a sanitized version and mark the actual command as sensitive
        logger.info(f"Starting Neo4j container {container_name} with Docker")
        exit_code, stdout, stderr = run_command(docker_cmd, sensitive=True)

        if exit_code != 0:
            logger.error(f"Failed to start Neo4j container: {stderr}")
            return False, ""

        logger.info("Waiting for Neo4j to start...")
        time.sleep(20)  # Wait for Neo4j to initialize

    # Verify connection
    try:
        from neo4j import GraphDatabase

        driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_username, neo4j_password))

        with driver.session() as session:
            result = session.run("RETURN 1 as test")
            if result.single()["test"] == 1:
                logger.info(f"Connected to Neo4j instance at {neo4j_uri}")
                driver.close()

                # Update environment variables
                os.environ["NEO4J_URI"] = neo4j_uri
                os.environ["NEO4J_USERNAME"] = neo4j_username
                os.environ["NEO4J_PASSWORD"] = neo4j_password

                return True, neo4j_uri
    except Exception as e:
        logger.error(f"Could not connect to Neo4j after starting container: {e}")

    return False, ""


def ensure_ai_api_key() -> Tuple[bool, str, str]:
    """
    Ensure an AI API key is available.

    Returns:
        Tuple of (success, provider, key)
    """
    # Check existing environment variables
    providers = [
        ("anthropic", "ANTHROPIC_API_KEY"),
        ("openai", "OPENAI_API_KEY"),
    ]

    for provider, env_var in providers:
        api_key = os.environ.get(env_var)
        if api_key:
            logger.info(f"Using existing {provider} API key from environment")
            return True, provider, api_key

    # Prompt user for API key if running interactively
    if sys.stdout.isatty():
        logger.info("No AI API keys found in environment variables")

        print("\nTo enable AI features, please provide an API key:")
        print("1. Anthropic (Claude)")
        print("2. OpenAI (GPT-4)")
        print("3. Skip AI testing")

        choice = input("Enter your choice (1-3): ")

        if choice == "1":
            api_key = input("Enter your Anthropic API key: ")
            if api_key:
                os.environ["ANTHROPIC_API_KEY"] = api_key
                os.environ["INKLINK_AI_PROVIDER"] = "anthropic"
                return True, "anthropic", api_key
        elif choice == "2":
            api_key = input("Enter your OpenAI API key: ")
            if api_key:
                os.environ["OPENAI_API_KEY"] = api_key
                os.environ["INKLINK_AI_PROVIDER"] = "openai"
                return True, "openai", api_key

    logger.warning("No AI API keys available, AI features will be disabled")
    return False, "", ""


def ensure_remarkable_auth() -> bool:
    """
    Ensure reMarkable authentication is configured.

    Returns:
        True if authenticated, False otherwise
    """
    # Get rmapi path
    rmapi_success, rmapi_path = ensure_rmapi()
    if not rmapi_success:
        logger.error("Failed to install rmapi")
        return False

    # Check if already authenticated
    rm_config_dir = os.path.expanduser("~/.rmapi")
    rm_config_file = os.path.join(rm_config_dir, "config.json")

    if os.path.exists(rm_config_file):
        try:
            with open(rm_config_file, "r") as f:
                config = json.load(f)
                if "Token" in config and "DeviceToken" in config:
                    logger.info("reMarkable authentication already configured")
                    return True
        except Exception as e:
            logger.warning(f"Error reading rmapi config: {e}")

    # Run rmapi to authenticate
    if sys.stdout.isatty():
        logger.info("reMarkable authentication required")
        print(
            "\nTo use reMarkable Cloud features, you need to authenticate with your reMarkable account."
        )
        print("Please follow the instructions to complete the authentication process.")

        # Run rmapi interactively
        exit_code, stdout, stderr = run_command([rmapi_path])

        # Check if authentication succeeded
        if os.path.exists(rm_config_file):
            try:
                with open(rm_config_file, "r") as f:
                    config = json.load(f)
                    if "Token" in config and "DeviceToken" in config:
                        logger.info("reMarkable authentication completed successfully")
                        return True
            except Exception:
                pass

    logger.warning("reMarkable authentication not configured")
    return False


# Make sure required Python packages are installed
ensure_python_package("neo4j")
ensure_python_package("requests")

# Set up logging
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("test_live_roundtrip")


class LiveRequest:
    """Live HTTP request for testing controllers."""

    def __init__(self, body=None, match_info=None):
        """Initialize with request body and match info."""
        self.body = body or {}
        self.match_info = match_info or {}
        self.headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    async def json(self):
        """Return the request body as JSON."""
        return self.body

    def get_accept_header(self):
        """Return the accept header."""
        return self.headers.get("Accept", "")


class LiveTestEnvironment:
    """Test environment for live testing with dependency installation."""

    def __init__(self):
        """Initialize the test environment with real services."""
        # Set up test environment
        self._setup_environment()

        # Ensure all dependencies are installed
        self._ensure_dependencies()

        # Create services
        self._create_services()

        # Create controllers
        self._create_controllers()

    def _setup_environment(self):
        """Set up the test environment directories."""
        # Create temporary directories
        self.test_dir = tempfile.mkdtemp(prefix="inklink_live_test_")
        self.temp_dir = os.path.join(self.test_dir, "temp")
        self.output_dir = os.path.join(self.test_dir, "output")
        self.qr_dir = os.path.join(self.test_dir, "qr")

        # Create directories
        os.makedirs(self.temp_dir, exist_ok=True)
        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(self.qr_dir, exist_ok=True)

        # Log status
        logger.info(f"Initialized test environment at {self.test_dir}")

    def _ensure_dependencies(self):
        """Ensure all dependencies are installed and configured."""
        # Ensure rmapi is installed
        rmapi_success, rmapi_path = ensure_rmapi()
        if rmapi_success:
            self.rmapi_path = rmapi_path
            logger.info(f"rmapi is available at {self.rmapi_path}")
        else:
            raise RuntimeError("Failed to install rmapi, which is required for testing")

        # Configure reMarkable authentication
        if not ensure_remarkable_auth():
            raise RuntimeError("reMarkable authentication is required for testing")

        # Ensure Neo4j is available
        neo4j_success, neo4j_uri = ensure_neo4j()
        if neo4j_success:
            self.neo4j_uri = neo4j_uri
            self.neo4j_username = os.environ.get("NEO4J_USERNAME", "neo4j")
            self.neo4j_password = os.environ.get("NEO4J_PASSWORD", "password")
            logger.info(f"Neo4j is available at {self.neo4j_uri}")
        else:
            raise RuntimeError("Failed to set up Neo4j, which is required for testing")

        # Configure AI service if possible
        ai_success, ai_provider, ai_key = ensure_ai_api_key()
        if ai_success:
            self.ai_provider = ai_provider
            self.ai_key = ai_key
            logger.info(f"AI service configured with provider: {self.ai_provider}")
        else:
            raise RuntimeError("AI API key is required for testing")

    def _create_services(self):
        """Create real service instances."""
        # Core services for document processing
        self.qr_service = QRCodeService(self.qr_dir)
        self.document_service = DocumentService(self.temp_dir)
        self.remarkable_service = RemarkableService(self.rmapi_path)
        self.web_scraper = WebScraperService()
        self.pdf_service = PDFService(self.temp_dir, self.output_dir)

        # AI service
        self.ai_service = AIService(provider=self.ai_provider, api_key=self.ai_key)

        # Knowledge graph service
        self.kg_service = KnowledgeGraphService(
            uri=self.neo4j_uri,
            username=self.neo4j_username,
            password=self.neo4j_password,
        )

        # Verify all services are working
        if not self.kg_service.is_connected():
            raise RuntimeError(f"Failed to connect to Neo4j at {self.neo4j_uri}")

    def _create_controllers(self):
        """Create controllers with real services."""
        # Create the share controller
        self.share_controller = ShareController(
            qr_service=self.qr_service,
            document_service=self.document_service,
            remarkable_service=self.remarkable_service,
            web_scraper=self.web_scraper,
        )

        # Create other controllers as needed
        self.ingest_controller = IngestController(
            services={
                "web_scraper": self.web_scraper,
                "document_service": self.document_service,
                "remarkable_service": self.remarkable_service,
                "pdf_service": self.pdf_service,
                "ai_service": self.ai_service,
            }
        )

        # Create knowledge graph controller
        self.kg_controller = KnowledgeGraphController(self.kg_service)

    def cleanup(self):
        """Clean up the test environment."""
        try:
            shutil.rmtree(self.test_dir)
            logger.info(f"Cleaned up test directory {self.test_dir}")
        except Exception as e:
            logger.error(f"Error cleaning up test directory: {e}")

        # Clean up Neo4j container if we started one
        try:
            exit_code, stdout, stderr = run_command(
                ["docker", "ps", "-q", "-f", "name=inklink_neo4j_test"]
            )
            if stdout.strip():
                logger.info("Stopping Neo4j container...")
                run_command(["docker", "stop", "inklink_neo4j_test"])
                run_command(["docker", "rm", "inklink_neo4j_test"])
        except Exception as e:
            logger.error(f"Error cleaning up Neo4j container: {e}")


@pytest.fixture(scope="module")
def live_env():
    """Fixture for live test environment."""
    env = LiveTestEnvironment()
    yield env
    env.cleanup()


def test_live_share_url(live_env):
    """Test the share controller with a real URL and reMarkable upload."""
    # Create request with test URL
    request = LiveRequest({"url": "https://example.com/"})

    # Process URL
    response = asyncio.run(live_env.share_controller.share_url(request))

    # Verify response indicates success
    assert response.status == 200, f"Expected 200 status code, got {response.status}"

    # Verify response body
    body_text = asyncio.run(response.text())
    import json

    body = json.loads(body_text)

    assert body["success"] is True, f"Expected success, got {body}"
    assert (
        "uploaded" in body.get("message", "").lower()
    ), f"Expected 'uploaded' in message, got {body.get('message')}"

    logger.info("Live share URL test passed")


def test_live_knowledge_graph(live_env):
    """Test the knowledge graph controller with a real Neo4j connection."""
    # Verify Neo4j connection
    assert live_env.kg_service.is_connected(), "Neo4j connection failed"

    # Create a test entity
    test_entity_name = f"Test_Entity_{os.getpid()}"

    # Create entity request
    create_request = LiveRequest(
        {
            "name": test_entity_name,
            "type": "TestEntity",
            "observations": ["Live test observation"],
        }
    )

    try:
        # Create entity
        create_response = asyncio.run(
            live_env.kg_controller.create_entity(create_request)
        )

        # Verify creation success
        assert (
            create_response.status == 201
        ), f"Expected 201 status code, got {create_response.status}"

        # Get the entity
        get_request = LiveRequest(match_info={"name": test_entity_name})
        get_response = asyncio.run(live_env.kg_controller.get_entity(get_request))

        # Verify entity retrieval
        assert (
            get_response.status == 200
        ), f"Expected 200 status code, got {get_response.status}"

        # Parse response
        get_body_text = asyncio.run(get_response.text())
        import json

        entity = json.loads(get_body_text)

        # Verify entity data
        assert (
            entity["name"] == test_entity_name
        ), f"Expected name {test_entity_name}, got {entity['name']}"
        assert (
            entity["type"] == "TestEntity"
        ), f"Expected type TestEntity, got {entity['type']}"
        assert (
            "observations" in entity["properties"]
        ), "observations not found in entity properties"

        logger.info("Live knowledge graph test passed")

    finally:
        # Clean up - delete the test entity
        try:
            delete_request = LiveRequest(match_info={"name": test_entity_name})
            result = asyncio.run(live_env.kg_controller.delete_entity(delete_request))
            logger.info(
                f"Test entity {test_entity_name} deleted with status {result.status}"
            )
        except Exception as e:
            logger.error(f"Error deleting test entity: {e}")


def test_live_pdf_processing(live_env):
    """Test PDF processing with real PDF and reMarkable upload."""
    # Download a sample PDF
    import requests

    # Sample PDF URL (Using a stable PDF from Adobe)
    pdf_url = "https://www.adobe.com/content/dam/Adobe/en/devnet/pdf/pdfs/pdf_reference_archives/PDFReference.pdf"

    # Download the PDF
    logger.info(f"Downloading sample PDF from {pdf_url}")
    pdf_response = requests.get(pdf_url)
    pdf_path = os.path.join(live_env.temp_dir, "sample.pdf")

    with open(pdf_path, "wb") as f:
        f.write(pdf_response.content)

    logger.info(f"Downloaded PDF to {pdf_path}")

    # Generate QR code for source URL
    qr_path, _ = live_env.qr_service.generate_qr(pdf_url)

    # Process PDF
    pdf_info = live_env.pdf_service.process_pdf(pdf_path, qr_path)

    # Verify PDF processing result
    assert pdf_info is not None, "PDF processing failed"
    assert "path" in pdf_info, "PDF path not found in processing result"

    # Upload to reMarkable
    success, message = live_env.remarkable_service.upload(
        pdf_info["path"], "Live Test PDF"
    )

    # Verify upload
    assert success, f"PDF upload failed: {message}"
    logger.info(f"PDF uploaded successfully: {message}")

    logger.info("Live PDF processing test passed")


def test_live_ai_integration(live_env):
    """Test AI integration with real API calls."""
    # Simple query for the AI
    query = "Summarize the key features of InkLink in 3 bullet points."

    # Get response
    response = live_env.ai_service.ask(query)

    # Verify response is meaningful
    assert response, "AI service returned empty response"
    assert len(response) > 50, "AI response too short, may be incomplete"

    # Count bullet points (a rough check)
    bullets = response.count("- ")
    assert bullets >= 3, f"Expected at least 3 bullet points, found {bullets}"

    logger.info("Live AI integration test passed")


def test_live_web_scraper(live_env):
    """Test the web scraper with a real URL."""
    # Scrape a test URL
    result = live_env.web_scraper.scrape("https://example.com/")

    # Verify basic scrape results
    assert result is not None, "Web scraper returned None"
    assert "title" in result, "Title not found in scrape results"
    assert (
        "Example Domain" in result["title"]
    ), f"Expected 'Example Domain' in title, got {result['title']}"
    assert (
        "structured_content" in result
    ), "structured_content not found in scrape results"

    logger.info("Live web scraper test passed")


if __name__ == "__main__":
    """Run all tests directly."""
    # Skip if live test flag not set
    if not os.environ.get("INKLINK_TEST_LIVE", "").lower() == "true":
        print("Live tests skipped. Set INKLINK_TEST_LIVE=true to run.")
        sys.exit(0)

    # Create test environment
    env = LiveTestEnvironment()

    try:
        # Run tests
        test_live_web_scraper(env)

        if env.remarkable_service:
            test_live_share_url(env)

        if neo4j_installed and env.kg_service:
            test_live_knowledge_graph(env)

        print("All live tests passed!")

    finally:
        # Clean up
        env.cleanup()
