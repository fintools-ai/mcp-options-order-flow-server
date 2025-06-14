"""Options monitoring configuration tool for MCP"""

import logging
from typing import Dict, List, Any
import json

from src.storage.grpc_client import OptionsOrderFlowGRPCClient

logger = logging.getLogger(__name__)


async def configure_options_monitoring(
    ticker: str,
    configurations: List[Dict[str, Any]]
) -> str:
    """
    Configure options monitoring for a ticker
    
    Args:
        ticker: Stock ticker symbol
        configurations: List of configuration dictionaries
        
    Returns:
        XML-formatted configuration status
    """
    try:
        # Validate request
        if not ticker:
            return build_error_response("Ticker is required")
            
        if not configurations:
            return build_error_response("At least one configuration is required")
            
        # Get gRPC client
        grpc_client = OptionsOrderFlowGRPCClient()
        
        # Process each configuration
        processed_configs = []
        
        for cfg in configurations:
            logger.info(f"Processing configuration: {cfg}")
            
            expiration = cfg.get("expiration")
            strike_range = cfg.get("strike_range", [])
            include_both_types = cfg.get("include_both_types", True)
            
            if not expiration or not strike_range:
                logger.warning(f"Skipping invalid configuration: {cfg}")
                continue
            
            # Prepare strikes and option types
            strikes = [float(s) for s in strike_range]
            option_types = ["C", "P"] if include_both_types else ["C"]
            
            logger.info(f"Configuring monitoring for {ticker} expiration {expiration}: strikes {strikes}, types {option_types}")
            
            # Configure monitoring via gRPC
            config_result = await grpc_client.configure_options_monitoring(
                ticker=ticker,
                expiration=expiration,
                strikes=strikes,
                option_types=option_types,
                action="ADD"
            )
            
            if not config_result:
                logger.error(f"Failed to configure monitoring for {ticker} {expiration}")
                continue
            
            if config_result.get('status') == 'error':
                logger.error(f"Error configuring monitoring: {config_result.get('message')}")
                continue
            
            logger.info(f"Successfully configured monitoring: {config_result}")
            
            processed_configs.append({
                "expiration": expiration,
                "strikes_added": strikes,
                "strikes_removed": [],
                "current_strike_range": strikes,
                "contracts_added": config_result.get('contracts_added', 0),
                "total_contracts": config_result.get('total_contracts_monitored', 0)
            })
            
        # Build response
        return build_success_response(ticker, processed_configs)
        
    except Exception as e:
        logger.exception(f"Error configuring options monitoring: {e}")
        return build_error_response(str(e))


async def get_monitoring_status(ticker: str) -> str:
    """
    Get current monitoring configuration for a ticker
    
    Args:
        ticker: Stock ticker symbol
        
    Returns:
        XML-formatted monitoring status
    """
    try:
        # Get gRPC client
        grpc_client = OptionsOrderFlowGRPCClient()
        
        # Get monitoring status via gRPC
        status_result = await grpc_client.get_monitoring_status(ticker)
        
        if not status_result:
            return f"""<monitoring_status ticker="{ticker}" status="error">
    <message>Failed to get monitoring status from data broker</message>
    <suggestion>Check if the data broker is running</suggestion>
</monitoring_status>"""
        
        if status_result.get('status') == 'error':
            return f"""<monitoring_status ticker="{ticker}" status="error">
    <message>{status_result.get('message', 'Unknown error')}</message>
</monitoring_status>"""
        
        # Get monitoring configurations
        configs = status_result.get('monitoring_configs', [])
        
        if not configs:
            return f"""<monitoring_status ticker="{ticker}" status="no_monitoring">
    <message>No monitoring configured for {ticker}</message>
    <suggestion>Use configure_options_monitoring_tool to set up monitoring</suggestion>
</monitoring_status>"""
            
        # Build response with configurations
        xml = f"""<monitoring_status ticker="{ticker}" status="active">
    <configurations count="{len(configs)}">"""
        
        for config in configs:
            expiration = config.get('expiration', 0)
            strikes = config.get('strikes', [])
            option_types = config.get('option_types', [])
            contract_count = config.get('contract_count', 0)
            configured_at = config.get('configured_at', '')
            is_active = config.get('is_active', True)
            
            include_both_types = len(option_types) > 1 or 'P' in option_types
            
            xml += f"""
        <configuration expiration="{expiration}" contract_count="{contract_count}" is_active="{is_active}">
            <strikes count="{len(strikes)}">"""
            
            for strike in strikes:
                xml += f"""
                <strike price="{strike}" types="{'both' if include_both_types else 'calls_only'}" />"""
                
            xml += f"""
            </strikes>
            <option_types>{', '.join(option_types)}</option_types>
            <configured_at>{configured_at}</configured_at>
        </configuration>"""
        
        xml += """
    </configurations>
</monitoring_status>"""
        
        return xml
        
    except Exception as e:
        logger.exception(f"Error getting monitoring status: {e}")
        return f"""<monitoring_status ticker="{ticker}" error="true">
    <error_message>{str(e)}</error_message>
</monitoring_status>"""


def build_success_response(ticker: str, processed_configs: List[Dict[str, Any]]) -> str:
    """Build success response in XML format"""
    xml = f"""<options_monitoring_config ticker="{ticker}" status="success">
    <processed_configurations count="{len(processed_configs)}">"""
    
    for config in processed_configs:
        expiration = config.get('expiration')
        strikes_added = config.get('strikes_added', [])
        strikes_removed = config.get('strikes_removed', [])
        current_strikes = config.get('current_strike_range', [])
        
        xml += f"""
        <configuration expiration="{expiration}">
            <strikes_added count="{len(strikes_added)}">"""
        
        for strike in strikes_added:
            xml += f"""
                <strike>{strike}</strike>"""
            
        xml += """
            </strikes_added>
            <strikes_removed count="0">"""
        
        for strike in strikes_removed:
            xml += f"""
                <strike>{strike}</strike>"""
            
        xml += f"""
            </strikes_removed>
            <current_strikes count="{len(current_strikes)}">"""
        
        for strike in current_strikes:
            xml += f"""
                <strike>{strike}</strike>"""
            
        xml += """
            </current_strikes>
        </configuration>"""
    
    xml += """
    </processed_configurations>
</options_monitoring_config>"""
    
    return xml


def build_error_response(error_message: str) -> str:
    """Build error response in XML format"""
    return f"""<options_monitoring_config status="error">
    <error_message>{error_message}</error_message>
    <expected_format>
        <ticker>Stock ticker symbol (e.g., SPY)</ticker>
        <configurations>
            <configuration>
                <expiration>YYYYMMDD format (e.g., 20240419)</expiration>
                <strike_range>List of strike prices (e.g., [400, 405, 410])</strike_range>
                <include_both_types>true or false (default: true)</include_both_types>
            </configuration>
        </configurations>
    </expected_format>
</options_monitoring_config>"""
