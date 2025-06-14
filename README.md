# MCP Options Order Flow Server

[![Python](https://img.shields.io/badge/Python-3.8%2B-blue?logo=python&logoColor=white)](https://python.org)
[![MCP](https://img.shields.io/badge/MCP-Compatible-green?logo=data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjQiIGhlaWdodD0iMjQiIHZpZXdCb3g9IjAgMCAyNCAyNCIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KPHBhdGggZD0iTTEyIDJMMTMuMDkgOC4yNkwyMCA5TDEzLjA5IDE1Ljc0TDEyIDIyTDEwLjkxIDE1Ljc0TDQgOUwxMC45MSA4LjI2TDEyIDJaIiBmaWxsPSJjdXJyZW50Q29sb3IiLz4KPC9zdmc+)](https://modelcontextprotocol.io)
[![FastMCP](https://img.shields.io/badge/FastMCP-Framework-orange)](https://github.com/jlowin/fastmcp)
[![gRPC](https://img.shields.io/badge/gRPC-Protocol-blue?logo=grpc)](https://grpc.io)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A high-performance Model Context Protocol (MCP) server for comprehensive options order flow analysis. This server provides real-time options order flow data, pattern detection, and institutional bias analysis through an intuitive MCP interface.

## 🚀 Features

- **Real-time Options Flow Analysis**: Monitor options order flow across multiple contracts with sub-10ms response times
- **Advanced Pattern Detection**: Identify sweeps, blocks, and unusual volume patterns with institutional-grade algorithms
- **Institutional Bias Tracking**: Monitor smart money positioning and directional sentiment
- **Historical Trend Analysis**: 30-minute interval analysis with key directional changes
- **Dynamic Monitoring**: Configure and monitor specific strike ranges and expirations without restarts
- **High Performance**: Built for production use with distributed Go+Python architecture

## 🏗️ Architecture

This MCP server integrates with the **mcp-trading-data-broker** Go service to provide:

```
┌─────────────────────┐    gRPC     ┌─────────────────────┐    WebSocket    ┌─────────────────────┐
│ MCP Options Server  │ ──────────► │ mcp-trading-data-   │ ──────────────► │ Market Data         │
│ (Python)            │             │ broker (Go)         │                 │ Provider            │
│                     │             │                     │                 │                     │
│ • MCP Tools         │             │ • Options Analysis  │                 │ • Options Quotes    │
│ • XML Formatting    │             │ • Pattern Detection │                 │ • Real-time Data    │
│ • Context Building  │             │ • Data Storage      │                 │                     │
└─────────────────────┘             └─────────────────────┘                 └─────────────────────┘
```

## 📋 Prerequisites

1. **mcp-trading-data-broker**: The Go-based data broker service
   - Provides gRPC server on port 9090
   - Handles real-time options data collection and analysis
   - Must be running before starting this MCP server

2. **Python 3.8+**: Required for MCP server
3. **Network Access**: For gRPC communication between services

## ⚡ Quick Start

### 1. Installation

```bash
# Clone the repository
git clone <repository-url>
cd mcp-options-order-flow-server

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On macOS/Linux
# venv\Scripts\activate     # On Windows

# Install dependencies
pip install -r requirements.txt
```

### 2. Configuration

Set environment variables:

```bash
# gRPC Data Broker Connection
export GRPC_HOST=localhost
export GRPC_PORT=9090
export GRPC_TIMEOUT=30

# Optional: Custom logging
export LOG_LEVEL=INFO
```

### 3. Start the Server

```bash
# Method 1: Using the convenience script
python run_server.py

# Method 2: Using module execution 
python -m src.mcp_server

# Method 3: Direct execution
python src/mcp_server.py
```

### 4. Claude Desktop Integration

Add to your Claude Desktop MCP configuration:

```json
{
  "mcpServers": {
    "options-flow": {
      "command": "python",
      "args": ["run_server.py"],
      "cwd": "/path/to/mcp-options-order-flow-server",
      "env": {
        "GRPC_HOST": "localhost",
        "GRPC_PORT": "9090"
      }
    }
  }
}
```

## 🛠️ Available MCP Tools

### 1. `analyze_options_flow`
Get comprehensive options order flow analysis for a ticker.

**Parameters:**
- `ticker` (string): Stock ticker symbol (e.g., "SPY", "QQQ")

**Returns:** XML-formatted analysis including:
- Monitored contracts grouped by expiration and strike
- Current activity levels and directional bias
- Detected patterns with confidence scores
- Historical trend analysis with 30-minute intervals
- Institutional bias and most active strikes

### 2. `configure_options_monitoring_tool`
Configure options monitoring for specific contracts.

**Parameters:**
- `ticker` (string): Stock ticker symbol
- `configurations` (array): Configuration objects with:
  - `expiration` (integer): Expiration date in YYYYMMDD format
  - `strike_range` (array): List of strike prices to monitor
  - `include_both_types` (boolean): Monitor both calls and puts

**Example:**
```json
{
  "ticker": "SPY",
  "configurations": [
    {
      "expiration": 20240419,
      "strike_range": [400, 405, 410],
      "include_both_types": true
    }
  ]
}
```

### 3. `get_monitoring_status_tool`
Get current monitoring configuration status.

**Parameters:**
- `ticker` (string): Stock ticker symbol

**Returns:** XML-formatted status showing all actively monitored contracts

### 4. `data_broker_health_check`
Check connectivity and health status of the data broker.

**Returns:** Health status with connection details and response time metrics

## 💡 Example Usage

### 1. Configure Monitoring
```
"Please monitor SPY options for expiration 2024-04-19, strikes 400-410, both calls and puts"
```

### 2. Analyze Options Flow
```
"Analyze the current options flow for SPY"
```

### 3. Check Monitoring Status
```
"What options contracts are currently being monitored for SPY?"
```

## 🔧 Development

### Running Tests
```bash
python test_tools.py
```

### Code Formatting
```bash
black src/
isort src/
flake8 src/
```

### Health Check
```bash
# Test data broker connectivity
python -c "import asyncio; from src.storage.grpc_client import OptionsOrderFlowGRPCClient; print(asyncio.run(OptionsOrderFlowGRPCClient().health_check()))"
```

## 📊 Performance

- **Response Time**: <10ms for pre-calculated data
- **Throughput**: 1000-5000 transactions/second processing
- **Scalability**: 100+ concurrent option contracts
- **Memory Usage**: ~50-80MB total footprint
- **Real-time Processing**: 1-second aggregation intervals

## 🛡️ Error Handling

The server provides structured error responses with:
- Clear error messages
- Possible causes identification
- Actionable suggestions for resolution
- Graceful degradation when data broker is unavailable

## 🔍 Troubleshooting

**Connection Issues:**
- Ensure mcp-trading-data-broker is running on port 9090
- Check network connectivity between services
- Verify environment variables are set correctly

**No Data Available:**
- Configure monitoring for desired contracts first
- Allow time for data collection to begin
- Check data broker logs for WebSocket connectivity

**Performance Issues:**
- Monitor gRPC connection health
- Check data broker resource usage
- Verify Redis connectivity (if used by data broker)

## 📚 Technical Details

### Pattern Detection Types
- **SWEEP**: Fast directional moves with multiple transactions
- **BLOCK**: Large institutional trades with high volume
- **UNUSUAL_VOLUME**: Sustained elevated volume activity

### Data Organization
- **Real-time Processing**: 1-second aggregation intervals
- **Pattern Detection**: 5-second analysis cycles
- **Historical Analysis**: 30-minute trend intervals
- **TTL Management**: Automatic data cleanup

### XML Response Format
- Hierarchical structure: Expiration → Strike → Call/Put
- Rich metadata with timestamps and confidence scores
- Comprehensive summaries with institutional bias
- MCP-compliant formatting for optimal LLM consumption

## 📄 License

MIT License - see LICENSE file for details

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

## 📞 Support

For issues and questions:
- Check the troubleshooting section
- Review error messages for specific guidance
- Ensure all prerequisites are properly configured
