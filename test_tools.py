#!/usr/bin/env python
"""Test script for MCP Options Order Flow Server tools"""

import asyncio
import json
import sys
from datetime import datetime

# Add src to path
sys.path.insert(0, '.')

from src.tools.options_flow_tool import get_options_flow
from src.tools.options_monitoring_tool import configure_options_monitoring, get_monitoring_status


async def test_configure_monitoring():
    """Test configuring options monitoring"""
    print("\n=== Testing Configure Options Monitoring ===")
    
    ticker = "SPY"
    configurations = [
        {
            "expiration": 20240419,
            "strike_range": [400, 405, 410, 415],
            "include_both_types": True
        }
    ]
    
    print(f"Configuring monitoring for {ticker}")
    print(f"Configurations: {json.dumps(configurations, indent=2)}")
    
    result = await configure_options_monitoring(ticker, configurations)
    print("\nResult:")
    print(result)
    

async def test_get_monitoring_status():
    """Test getting monitoring status"""
    print("\n=== Testing Get Monitoring Status ===")
    
    ticker = "SPY"
    print(f"Getting monitoring status for {ticker}")
    
    result = await get_monitoring_status(ticker)
    print("\nResult:")
    print(result)
    

async def test_get_options_flow():
    """Test getting options flow analysis"""
    print("\n=== Testing Get Options Flow ===")
    
    ticker = "SPY"
    print(f"Getting options flow for {ticker}")
    
    result = await get_options_flow(ticker)
    print("\nResult:")
    print(result[:1000] + "..." if len(result) > 1000 else result)
    

async def main():
    """Run all tests"""
    print("MCP Options Order Flow Server - Test Suite")
    print(f"Started at: {datetime.now()}")
    
    try:
        # Test configuration
        await test_configure_monitoring()
        
        # Wait a bit
        await asyncio.sleep(2)
        
        # Test status
        await test_get_monitoring_status()
        
        # Test flow analysis
        await test_get_options_flow()
        
    except Exception as e:
        print(f"\nError during testing: {e}")
        import traceback
        traceback.print_exc()
        
    print(f"\nCompleted at: {datetime.now()}")


if __name__ == "__main__":
    asyncio.run(main())
