"""MCP Options Order Flow Server - Main entry point"""

from fastmcp import FastMCP
import os
import sys
import logging
from pathlib import Path
from typing import Dict, Any

# Add project root to Python path for absolute imports
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Configure logging
logging.basicConfig(
    level=getattr(logging, os.getenv("LOG_LEVEL", "INFO")),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stderr)]
)
logger = logging.getLogger(__name__)

# Import tool implementations
from src.tools.options_flow_tool import get_options_flow
from src.tools.options_monitoring_tool import configure_options_monitoring, get_monitoring_status

# Create MCP server instance
mcp = FastMCP("mcp-options-order-flow-server")


@mcp.tool()
async def analyze_options_flow(ticker: str) -> str:
    """
    Get comprehensive options order flow analysis for a ticker.
    
    This tool provides real-time analysis of options order flow including:
    - Monitored contracts with bid/ask data
    - Detected patterns (sweeps, blocks, unusual volume)
    - Institutional bias and directional signals
    - Historical trend analysis
    - Most active strikes
    
    Args:
        ticker: Stock ticker symbol (e.g., SPY, QQQ)
        
    Returns:
        XML-formatted comprehensive options flow analysis
    """
    try:
        result = await get_options_flow(ticker)
        return result
    except Exception as e:
        logger.error(f"Error analyzing options flow for {ticker}: {e}")
        return f"""<options_order_flow ticker="{ticker}" error="true">
    <error_message>{str(e)}</error_message>
    <suggestion>Please verify the ticker and ensure monitoring is configured</suggestion>
</options_order_flow>"""


@mcp.tool()
async def configure_options_monitoring_tool(
    ticker: str,
    configurations: list[Dict[str, Any]]
) -> str:
    """
    Configure options monitoring for specific contracts.
    
    This tool sets up monitoring for specific options contracts to track order flow.
    
    Args:
        ticker: Stock ticker symbol
        configurations: List of configuration objects, each containing:
            - expiration: Expiration date in YYYYMMDD format (e.g., 20240419)
            - strike_range: List of strike prices to monitor (e.g., [400, 405, 410])
            - include_both_types: Whether to monitor both calls and puts (default: true)
            
    Example:
        ticker = "SPY"
        configurations = [
            {
                "expiration": 20240419,
                "strike_range": [400, 405, 410],
                "include_both_types": true
            }
        ]
        
    Returns:
        XML-formatted configuration status
    """
    try:
        result = await configure_options_monitoring(ticker, configurations)
        return result
    except Exception as e:
        logger.error(f"Error configuring options monitoring: {e}")
        return f"""<options_monitoring_config ticker="{ticker}" error="true">
    <error_message>{str(e)}</error_message>
    <suggestion>Please check the configuration format and try again</suggestion>
</options_monitoring_config>"""


@mcp.tool()
async def get_monitoring_status_tool(ticker: str) -> str:
    """
    Get current options monitoring configuration status.
    
    This tool shows which options contracts are currently being monitored for a ticker.
    
    Args:
        ticker: Stock ticker symbol
        
    Returns:
        XML-formatted monitoring status
    """
    try:
        result = await get_monitoring_status(ticker)
        return result
    except Exception as e:
        logger.error(f"Error getting monitoring status: {e}")
        return f"""<monitoring_status ticker="{ticker}" error="true">
    <error_message>{str(e)}</error_message>
</monitoring_status>"""


@mcp.tool()
async def data_broker_health_check() -> str:
    """
    Check the health and connectivity status of the data broker.
    
    This tool verifies that the mcp-trading-data-broker service is running and accessible.
    
    Returns:
        XML-formatted health check status
    """
    try:
        from src.storage.grpc_client import OptionsOrderFlowGRPCClient
        
        # Create client and perform health check
        client = OptionsOrderFlowGRPCClient()
        health_status = await client.health_check()
        await client.close()
        
        if health_status.get('status') == 'healthy':
            return f"""<data_broker_health status="healthy">
    <connection>
        <host>{health_status.get('host')}</host>
        <port>{health_status.get('port')}</port>
        <connected>{health_status.get('connected')}</connected>
        <response_time_ms>{health_status.get('response_time_ms', 0):.2f}</response_time_ms>
    </connection>
    <timestamp>{health_status.get('timestamp')}</timestamp>
    <message>Data broker is accessible and responding</message>
</data_broker_health>"""
        else:
            return f"""<data_broker_health status="unhealthy">
    <error>{health_status.get('error')}</error>
    <timestamp>{health_status.get('timestamp')}</timestamp>
    <suggestions>
        <suggestion>Verify mcp-trading-data-broker is running</suggestion>
        <suggestion>Check network connectivity to {os.getenv('GRPC_HOST', 'localhost')}:{os.getenv('GRPC_PORT', '9090')}</suggestion>
        <suggestion>Ensure gRPC service is properly configured</suggestion>
    </suggestions>
</data_broker_health>"""
        
    except Exception as e:
        logger.error(f"Error performing health check: {e}")
        return f"""<data_broker_health status="error">
    <error_message>{str(e)}</error_message>
    <suggestions>
        <suggestion>Install required dependencies: pip install grpcio grpcio-tools protobuf</suggestion>
        <suggestion>Ensure mcp-trading-data-broker is running on {os.getenv('GRPC_HOST', 'localhost')}:{os.getenv('GRPC_PORT', '9090')}</suggestion>
        <suggestion>Check protobuf generation: python -m grpc_tools.protoc --proto_path=path/to/proto --python_out=src/proto --grpc_python_out=src/proto options_order_flow.proto</suggestion>
    </suggestions>
</data_broker_health>"""


def main():
    """Main entry point"""
    logger.info("Starting MCP Options Order Flow Server")
    logger.info(f"Data broker: {os.getenv('GRPC_HOST', 'localhost')}:{os.getenv('GRPC_PORT', '9090')}")
    
    # Run the server
    try:
        mcp.run()
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
