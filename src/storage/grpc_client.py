"""Production gRPC client for options order flow data from mcp-trading-data-broker"""

import os
import grpc
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import asyncio

# Import generated protobuf classes
try:
    from src.proto import options_order_flow_pb2
    from src.proto import options_order_flow_pb2_grpc
except ImportError as e:
    logging.error(f"Failed to import protobuf classes. Run: python -m grpc_tools.protoc --proto_path=<path_to_proto> --python_out=src/proto --grpc_python_out=src/proto options_order_flow.proto")
    raise

logger = logging.getLogger(__name__)


class OptionsOrderFlowGRPCClient:
    """Production gRPC client for options order flow data access via mcp-trading-data-broker"""
    
    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        timeout: Optional[float] = None,
        max_retry_attempts: int = 3,
        retry_delay: float = 1.0
    ):
        """
        Initialize gRPC client
        
        Args:
            host: gRPC server host (defaults to env or localhost)
            port: gRPC server port (defaults to env or 9090)
            timeout: Request timeout in seconds (defaults to 30)
            max_retry_attempts: Maximum retry attempts for failed requests
            retry_delay: Delay between retry attempts in seconds
        """
        self.host = host or os.getenv('GRPC_HOST', 'localhost')
        self.port = int(port or os.getenv('GRPC_PORT', 9090))
        self.timeout = timeout or float(os.getenv('GRPC_TIMEOUT', '30'))
        self.max_retry_attempts = max_retry_attempts
        self.retry_delay = retry_delay
        
        self._channel = None
        self._stub = None
        self._connected = False
        
    async def _ensure_connection(self):
        """Ensure gRPC connection is established"""
        if self._connected and self._channel and self._stub:
            return
            
        try:
            # Create async channel
            self._channel = grpc.aio.insecure_channel(f'{self.host}:{self.port}')
            
            # Test connection with a simple call timeout
            try:
                await asyncio.wait_for(
                    self._channel.check_connectivity_state(try_to_connect=True),
                    timeout=5.0
                )
            except asyncio.TimeoutError:
                # If check_connectivity_state isn't available, we'll proceed anyway
                # and let the actual RPC calls fail if the server isn't available
                pass
            
            # Create stub
            self._stub = options_order_flow_pb2_grpc.OptionsOrderFlowServiceStub(self._channel)
            
            self._connected = True
            logger.info(f"Connected to Options Order Flow gRPC server at {self.host}:{self.port}")
            
        except Exception as e:
            logger.error(f"Failed to connect to gRPC server at {self.host}:{self.port}: {e}")
            self._connected = False
            raise ConnectionError(f"Unable to connect to data broker: {e}")
    
    async def close(self):
        """Close gRPC connection"""
        if self._channel:
            await self._channel.close()
            self._channel = None
            self._stub = None
            self._connected = False
            logger.info("gRPC connection closed")
    
    async def _execute_with_retry(self, operation_name: str, operation_func, *args, **kwargs):
        """Execute gRPC operation with retry logic"""
        for attempt in range(self.max_retry_attempts):
            try:
                await self._ensure_connection()
                return await operation_func(*args, **kwargs)
                
            except grpc.aio.AioRpcError as e:
                logger.warning(f"gRPC error in {operation_name} (attempt {attempt + 1}/{self.max_retry_attempts}): {e.code()} - {e.details()}")
                
                if e.code() in [grpc.StatusCode.UNAVAILABLE, grpc.StatusCode.DEADLINE_EXCEEDED]:
                    # Reset connection for connection issues
                    self._connected = False
                    if attempt < self.max_retry_attempts - 1:
                        await asyncio.sleep(self.retry_delay * (2 ** attempt))  # Exponential backoff
                        continue
                        
                # For other errors, don't retry
                raise
                
            except Exception as e:
                logger.error(f"Unexpected error in {operation_name} (attempt {attempt + 1}/{self.max_retry_attempts}): {e}")
                if attempt < self.max_retry_attempts - 1:
                    await asyncio.sleep(self.retry_delay)
                    continue
                raise
        
        raise ConnectionError(f"Failed to execute {operation_name} after {self.max_retry_attempts} attempts")
    
    async def get_options_order_flow_snapshot(
        self,
        ticker: str,
        expiration: Optional[int] = None,
        strikes: Optional[List[float]] = None,
        option_types: Optional[List[str]] = None,
        history_seconds: int = 1200,
        include_patterns: bool = True,
        include_aggregations: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        Get comprehensive options order flow snapshot
        
        Args:
            ticker: Stock ticker symbol
            expiration: Option expiration (YYYYMMDD format), None for all
            strikes: List of strike prices, None for all
            option_types: List of option types (C, P), None for all
            history_seconds: Seconds of history to include
            include_patterns: Include pattern analysis
            include_aggregations: Include aggregation data
            
        Returns:
            Dictionary with snapshot data or None on error
        """
        async def _execute():
            # Create request
            request = options_order_flow_pb2.GetOptionsOrderFlowSnapshotRequest()
            request.ticker = ticker
            request.expiration = expiration or 0
            if strikes:
                request.strikes.extend(strikes)
            if option_types:
                request.option_types.extend(option_types)
            else:
                request.option_types.extend(["C", "P"])
            request.history_seconds = history_seconds
            request.include_patterns = include_patterns
            request.include_aggregations = include_aggregations
            
            # Make gRPC call
            response = await self._stub.GetOptionsOrderFlowSnapshot(
                request, 
                timeout=self.timeout
            )
            
            # Convert response to dictionary
            return self._parse_snapshot_response(response)
        
        try:
            return await self._execute_with_retry("get_options_order_flow_snapshot", _execute)
        except Exception as e:
            logger.error(f"Error getting options order flow snapshot for {ticker}: {e}")
            return None
    
    async def configure_options_monitoring(
        self,
        ticker: str,
        expiration: int,
        strikes: List[float],
        option_types: List[str],
        action: str = "ADD"
    ) -> Optional[Dict[str, Any]]:
        """
        Configure options monitoring
        
        Args:
            ticker: Stock ticker symbol
            expiration: Option expiration (YYYYMMDD format)
            strikes: List of strike prices to monitor
            option_types: List of option types (C, P)
            action: Action to take (ADD, REMOVE, REPLACE)
            
        Returns:
            Dictionary with configuration result or None on error
        """
        async def _execute():
            # Create request
            request = options_order_flow_pb2.ConfigureOptionsOrderFlowRequest()
            request.ticker = ticker
            request.expiration = expiration
            request.strikes.extend(strikes)
            request.option_types.extend(option_types)
            request.action = action
            
            # Make gRPC call
            response = await self._stub.ConfigureOptionsOrderFlowMonitoring(
                request,
                timeout=self.timeout
            )
            
            # Convert response to dictionary
            return self._parse_config_response(response)
        
        try:
            return await self._execute_with_retry("configure_options_monitoring", _execute)
        except Exception as e:
            logger.error(f"Error configuring options monitoring for {ticker}: {e}")
            return None
    
    async def get_monitoring_status(self, ticker: str) -> Optional[Dict[str, Any]]:
        """
        Get current monitoring status for a ticker
        
        Args:
            ticker: Stock ticker symbol
            
        Returns:
            Dictionary with monitoring status or None on error
        """
        async def _execute():
            # Create request
            request = options_order_flow_pb2.GetOptionsOrderFlowStatusRequest()
            request.ticker = ticker
            
            # Make gRPC call
            response = await self._stub.GetOptionsOrderFlowMonitoringStatus(
                request,
                timeout=self.timeout
            )
            
            # Convert response to dictionary
            return self._parse_status_response(response)
        
        try:
            return await self._execute_with_retry("get_monitoring_status", _execute)
        except Exception as e:
            logger.error(f"Error getting monitoring status for {ticker}: {e}")
            return None
    
    # Response Parsing Methods
    
    def _parse_snapshot_response(self, response) -> Dict[str, Any]:
        """Parse snapshot response from protobuf to dictionary"""
        try:
            result = {
                'ticker': response.ticker,
                'snapshot_time': response.snapshot_time.ToJsonString() if response.HasField('snapshot_time') else datetime.now().isoformat(),
                'status': response.status,
                'message': response.message,
                'contracts': [],
                'patterns': [],
                'summary': {}
            }
            
            # Parse contracts
            for contract in response.contracts:
                contract_data = {
                    'ticker': contract.ticker,
                    'expiration': contract.expiration,
                    'strike': contract.strike,
                    'option_type': contract.option_type,
                    'symbol': contract.symbol,
                    'is_monitored': contract.is_monitored,
                    'last_update': contract.last_update.ToJsonString() if contract.HasField('last_update') else '',
                    'latest_aggregation': None,
                    'recent_patterns': []
                }
                
                # Parse latest aggregation
                if contract.HasField('latest_aggregation'):
                    agg = contract.latest_aggregation
                    contract_data['latest_aggregation'] = {
                        'timestamp': agg.timestamp.ToJsonString() if agg.HasField('timestamp') else '',
                        'total_volume': agg.total_volume,
                        'bid_volume': agg.bid_volume,
                        'ask_volume': agg.ask_volume,
                        'avg_bid': agg.avg_bid,
                        'avg_ask': agg.avg_ask,
                        'transaction_count': agg.transaction_count,
                        'imbalance': agg.imbalance,
                        'volume_weighted_price': agg.volume_weighted_price
                    }
                
                # Parse recent patterns
                for pattern in contract.recent_patterns:
                    pattern_data = {
                        'type': pattern.type,
                        'timestamp': pattern.timestamp.ToJsonString() if pattern.HasField('timestamp') else '',
                        'confidence': pattern.confidence,
                        'description': pattern.description,
                        'direction': pattern.direction,
                        'total_volume': pattern.total_volume,
                        'duration_seconds': pattern.duration_seconds,
                        'metrics': dict(pattern.metrics) if pattern.metrics else {}
                    }
                    contract_data['recent_patterns'].append(pattern_data)
                
                result['contracts'].append(contract_data)
            
            # Parse patterns
            for pattern in response.patterns:
                pattern_data = {
                    'type': pattern.type,
                    'ticker': pattern.ticker,
                    'expiration': pattern.expiration,
                    'strike': pattern.strike,
                    'option_type': pattern.option_type,
                    'timestamp': pattern.timestamp.ToJsonString() if pattern.HasField('timestamp') else '',
                    'confidence': pattern.confidence,
                    'description': pattern.description,
                    'direction': pattern.direction,
                    'total_volume': pattern.total_volume,
                    'duration_seconds': pattern.duration_seconds,
                    'metrics': dict(pattern.metrics) if pattern.metrics else {}
                }
                result['patterns'].append(pattern_data)
            
            # Parse summary
            if response.HasField('summary'):
                summary = response.summary
                result['summary'] = {
                    'total_contracts_monitored': summary.total_contracts_monitored,
                    'active_patterns': summary.active_patterns,
                    'total_volume': summary.total_volume,
                    'call_volume': summary.call_volume,
                    'put_volume': summary.put_volume,
                    'put_call_ratio': summary.put_call_ratio,
                    'sweep_patterns': summary.sweep_patterns,
                    'block_patterns': summary.block_patterns,
                    'unusual_volume_patterns': summary.unusual_volume_patterns,
                    'dominant_flow': summary.dominant_flow,
                    'hot_contracts': []
                }
                
                # Parse hot contracts
                for hot_contract in summary.hot_contracts:
                    hot_data = {
                        'symbol': hot_contract.symbol,
                        'ticker': hot_contract.ticker,
                        'expiration': hot_contract.expiration,
                        'strike': hot_contract.strike,
                        'option_type': hot_contract.option_type,
                        'volume': hot_contract.volume,
                        'pattern_count': hot_contract.pattern_count,
                        'activity_score': hot_contract.activity_score
                    }
                    result['summary']['hot_contracts'].append(hot_data)
            
            return result
            
        except Exception as e:
            logger.error(f"Error parsing snapshot response: {e}")
            return {'status': 'error', 'message': str(e)}
    
    def _parse_config_response(self, response) -> Dict[str, Any]:
        """Parse configuration response from protobuf to dictionary"""
        try:
            return {
                'status': response.status,
                'message': response.message,
                'ticker': response.ticker,
                'expiration': response.expiration,
                'contracts_added': response.contracts_added,
                'contracts_removed': response.contracts_removed,
                'total_contracts_monitored': response.total_contracts_monitored,
                'contract_symbols': list(response.contract_symbols),
                'timestamp': response.timestamp.ToJsonString() if response.HasField('timestamp') else datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Error parsing config response: {e}")
            return {'status': 'error', 'message': str(e)}
    
    def _parse_status_response(self, response) -> Dict[str, Any]:
        """Parse status response from protobuf to dictionary"""
        try:
            result = {
                'status': response.status,
                'message': response.message,
                'total_contracts_monitored': response.total_contracts_monitored,
                'total_tickers': response.total_tickers,
                'contracts_by_ticker': dict(response.contracts_by_ticker),
                'timestamp': response.timestamp.ToJsonString() if response.HasField('timestamp') else datetime.now().isoformat(),
                'monitoring_configs': []
            }
            
            # Parse monitoring configurations
            for config in response.configurations:
                config_data = {
                    'ticker': config.ticker,
                    'expiration': config.expiration,
                    'strikes': list(config.strikes),
                    'option_types': list(config.option_types),
                    'contract_count': config.contract_count,
                    'configured_at': config.configured_at.ToJsonString() if config.HasField('configured_at') else '',
                    'is_active': config.is_active
                }
                result['monitoring_configs'].append(config_data)
            
            return result
            
        except Exception as e:
            logger.error(f"Error parsing status response: {e}")
            return {'status': 'error', 'message': str(e)}
    
    # Legacy compatibility methods for existing code
    
    async def get_monitoring_configurations(self, ticker: str) -> List[Tuple[int, int]]:
        """Get all monitoring configurations for a ticker as (strike, expiration) tuples"""
        try:
            status = await self.get_monitoring_status(ticker)
            if not status or status.get('status') != 'success':
                return []
            
            configs = []
            for config in status.get('monitoring_configs', []):
                expiration = config.get('expiration', 0)
                strikes = config.get('strikes', [])
                for strike in strikes:
                    configs.append((int(strike), expiration))
            
            return configs
            
        except Exception as e:
            logger.error(f"Error getting monitoring configurations: {e}")
            return []
    
    async def get_monitoring_configurations_detailed(self, ticker: str) -> List[Dict[str, Any]]:
        """Get detailed monitoring configurations for a ticker"""
        try:
            status = await self.get_monitoring_status(ticker)
            if not status or status.get('status') != 'success':
                return []
            
            return status.get('monitoring_configs', [])
            
        except Exception as e:
            logger.error(f"Error getting detailed monitoring configurations: {e}")
            return []
    
    async def get_options_patterns(self, ticker: str, expiration: int, strike: float,
                            option_type: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent options patterns for a specific contract"""
        try:
            snapshot = await self.get_options_order_flow_snapshot(
                ticker=ticker,
                expiration=expiration,
                strikes=[strike],
                option_types=[option_type],
                history_seconds=3600,  # 1 hour
                include_patterns=True,
                include_aggregations=False
            )
            
            if not snapshot:
                return []
            
            # Find patterns for this contract
            patterns = []
            for pattern in snapshot.get('patterns', []):
                if (pattern.get('ticker') == ticker and
                    pattern.get('expiration') == expiration and
                    pattern.get('strike') == strike and
                    pattern.get('option_type') == option_type):
                    patterns.append(pattern)
            
            # Sort by timestamp (newest first) and limit
            patterns.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
            return patterns[:limit]
            
        except Exception as e:
            logger.error(f"Error getting options patterns: {e}")
            return []
    
    # Utility methods for formatting
    
    def format_expiration(self, expiration: int) -> str:
        """Format expiration date for display"""
        if not expiration:
            return "Unknown"
            
        exp_str = str(expiration)
        if len(exp_str) == 8:
            return f"{exp_str[4:6]}/{exp_str[6:8]}/{exp_str[0:4]}"
        return str(expiration)
        
    def format_strike(self, strike: float) -> str:
        """Format strike price for display"""
        return f"${strike:.2f}"

    # Health check methods
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on the gRPC connection"""
        try:
            await self._ensure_connection()
            
            # Try a simple request to verify the service is responding
            start_time = datetime.now()
            status = await self.get_monitoring_status("TEST")
            end_time = datetime.now()
            
            response_time_ms = (end_time - start_time).total_seconds() * 1000
            
            return {
                'status': 'healthy',
                'connected': self._connected,
                'host': self.host,
                'port': self.port,
                'response_time_ms': response_time_ms,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                'status': 'unhealthy',
                'connected': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }