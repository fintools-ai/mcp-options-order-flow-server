"""Options flow analysis tool for MCP"""

import asyncio
import logging
from typing import Optional
import nest_asyncio

# Enable nested event loops
nest_asyncio.apply()

from src.formatters.context_builder import OptionsContextBuilder
from src.formatters.xml_formatter import OptionsMCPFormatter
from src.storage.grpc_client import OptionsOrderFlowGRPCClient

logger = logging.getLogger(__name__)


def _run_async(coro):
    """Helper to run async code in potentially nested event loops"""
    try:
        loop = asyncio.get_running_loop()
        # If we're already in a running loop, we can await directly
        return coro
    except RuntimeError:
        # No running loop, create new one
        return asyncio.run(coro)


async def get_options_flow(ticker: str, history_minutes: int = 20) -> str:
    """
    Get comprehensive options order flow data for all monitored contracts of a ticker
    
    Args:
        ticker: Stock ticker symbol
        history_minutes: Minutes of history to include (default: 20)
        
    Returns:
        XML-formatted options flow analysis
    """
    try:
        # Get gRPC client
        grpc_client = OptionsOrderFlowGRPCClient()
        
        # Get comprehensive snapshot from data broker with timeout
        try:
            snapshot = await asyncio.wait_for(
                grpc_client.get_options_order_flow_snapshot(
                    ticker=ticker,
                    expiration=None,  # All expirations
                    strikes=None,     # All strikes
                    option_types=None,  # All option types
                    history_seconds=history_minutes * 60,
                    include_patterns=True,
                    include_aggregations=True
                ),
                timeout=30.0  # 30 second timeout
            )
        except asyncio.TimeoutError:
            return build_error_response(ticker, "Request timeout - data broker not responding")
        except Exception as e:
            return build_error_response(ticker, f"Connection error: {str(e)}")
        
        if not snapshot:
            return build_error_response(ticker, "Failed to get data from options order flow broker")
        
        if snapshot.get('status') == 'error':
            return build_error_response(ticker, snapshot.get('message', 'Unknown error from data broker'))
        
        # Create context builder (updated to use gRPC data)
        context_builder = OptionsContextBuilder(grpc_client)
        
        # Build comprehensive context from snapshot data
        context = await context_builder.build_comprehensive_response_from_snapshot(ticker, snapshot)
        
        # Format as MCP XML
        formatter = OptionsMCPFormatter()
        mcp_xml = formatter.format_comprehensive(context)
        
        # Close gRPC client
        await grpc_client.close()
        
        return mcp_xml
        
    except Exception as e:
        logger.exception(f"Error getting options flow for {ticker}: {e}")
        return build_error_response(ticker, str(e))


def build_error_response(ticker: str, error_message: str) -> str:
    """Build error response in MCP format"""
    return f"""<options_order_flow ticker="{ticker}" error="true">
    <error_message>{error_message}</error_message>
    <possible_causes>
        <cause>No monitoring configured for this ticker</cause>
        <cause>Data broker not running</cause>
        <cause>Network connectivity issue</cause>
    </possible_causes>
    <suggestions>
        <suggestion>Configure monitoring using configure_options_monitoring_tool</suggestion>
        <suggestion>Verify the ticker symbol is correct</suggestion>
        <suggestion>Check if the mcp-trading-data-broker is running</suggestion>
        <suggestion>Verify network connectivity to data broker</suggestion>
    </suggestions>
</options_order_flow>"""
