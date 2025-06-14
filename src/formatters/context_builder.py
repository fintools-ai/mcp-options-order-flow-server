"""Context builder for options order flow data"""

import time
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta

from src.storage.grpc_client import OptionsOrderFlowGRPCClient

logger = logging.getLogger(__name__)


class OptionsContextBuilder:
    """
    Builds MCP context for options order flow data.
    Creates a comprehensive view of options activity for specific contracts.
    """

    def __init__(
            self,
            grpc_client: Optional[OptionsOrderFlowGRPCClient] = None
    ):
        """
        Initialize Context Builder

        Args:
            grpc_client (OptionsOrderFlowGRPCClient, optional): gRPC client
        """
        self.logger = logging.getLogger('OptionsContextBuilder')
        self.grpc_client = grpc_client or OptionsOrderFlowGRPCClient()

    async def build_comprehensive_response_from_snapshot(self, ticker: str, snapshot: Dict[str, Any]) -> Dict[str, Any]:
        """
        Build comprehensive context from gRPC snapshot data
        
        Args:
            ticker (str): Ticker symbol
            snapshot (Dict[str, Any]): Snapshot data from gRPC
            
        Returns:
            Dict[str, Any]: Comprehensive context for MCP formatting
        """
        try:
            contracts = snapshot.get('contracts', [])
            patterns = snapshot.get('patterns', [])
            summary = snapshot.get('summary', {})
            
            # Transform contracts to our format
            monitored_contracts = []
            for contract in contracts:
                contract_data = self._transform_contract_from_snapshot(contract)
                if contract_data:
                    monitored_contracts.append(contract_data)
            
            # Create global summary from snapshot
            global_summary = self._create_global_summary_from_snapshot(summary, patterns, monitored_contracts)
            
            return {
                'ticker': ticker,
                'timestamp': snapshot.get('snapshot_time', datetime.now().isoformat()),
                'monitored_contracts': monitored_contracts,
                'summary': global_summary,
                'broker_status': snapshot.get('status', 'unknown'),
                'broker_message': snapshot.get('message', '')
            }
            
        except Exception as e:
            self.logger.error(f"Error building comprehensive response from snapshot: {e}")
            return {
                'ticker': ticker,
                'timestamp': datetime.now().isoformat(),
                'monitored_contracts': [],
                'summary': {},
                'error': str(e)
            }

    def _transform_contract_from_snapshot(self, contract: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Transform snapshot contract to our format"""
        try:
            # Get basic contract info
            ticker = contract.get('ticker', '')
            expiration = contract.get('expiration', 0)
            strike = contract.get('strike', 0)
            option_type = contract.get('option_type', '')
            
            # Get latest aggregation
            latest_agg = contract.get('latest_aggregation')
            
            # Get recent patterns
            recent_patterns = contract.get('recent_patterns', [])
            
            # Create current state from aggregation and patterns
            current_state = self._create_summary_from_snapshot_data(recent_patterns, latest_agg)
            
            # Build contract data
            contract_data = {
                'ticker': ticker,
                'expiration': expiration,
                'expiration_display': self.grpc_client.format_expiration(expiration),
                'strike': strike,
                'strike_display': self.grpc_client.format_strike(strike),
                'option_type': option_type,
                'symbol': contract.get('symbol', ''),
                'is_monitored': contract.get('is_monitored', False),
                'last_update': contract.get('last_update', ''),
                'patterns': recent_patterns,
                'current_state': current_state,
                'latest_aggregation': latest_agg,
                'historical_summary': {}  # Would need historical data for this
            }
            
            return contract_data
            
        except Exception as e:
            self.logger.error(f"Error transforming contract from snapshot: {e}")
            return None
    
    def _create_summary_from_snapshot_data(self, patterns: List[Dict[str, Any]], aggregation: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Create current state summary from snapshot data"""
        try:
            if not patterns and not aggregation:
                return {
                    'activity_level': 'LOW',
                    'dominant_direction': 'NEUTRAL',
                    'significance': 'LOW',
                    'recent_pattern_count': 0
                }
            
            # Count patterns by type
            pattern_types = {}
            buy_signals = 0
            sell_signals = 0
            
            for pattern in patterns:
                pattern_type = pattern.get('type', '')
                if pattern_type:
                    pattern_types[pattern_type] = pattern_types.get(pattern_type, 0) + 1
                
                # Count directional signals
                direction = pattern.get('direction', '')
                if 'BULLISH' in direction.upper() or 'BUY' in direction.upper():
                    buy_signals += 1
                elif 'BEARISH' in direction.upper() or 'SELL' in direction.upper():
                    sell_signals += 1
            
            # Determine dominant direction
            if buy_signals > sell_signals * 2:
                dominant_direction = 'STRONG_BUY'
            elif buy_signals > sell_signals:
                dominant_direction = 'BUY'
            elif sell_signals > buy_signals * 2:
                dominant_direction = 'STRONG_SELL'
            elif sell_signals > buy_signals:
                dominant_direction = 'SELL'
            else:
                dominant_direction = 'NEUTRAL'
            
            # Determine activity level based on patterns and volume
            total_volume = 0
            if aggregation:
                total_volume = aggregation.get('total_volume', 0)
            
            pattern_count = len(patterns)
            if pattern_count >= 10 or total_volume > 10000:
                activity_level = 'VERY_HIGH'
            elif pattern_count >= 5 or total_volume > 5000:
                activity_level = 'HIGH'
            elif pattern_count >= 2 or total_volume > 1000:
                activity_level = 'MEDIUM'
            else:
                activity_level = 'LOW'
            
            # Determine significance
            significance = 'LOW'
            for pattern in patterns:
                if pattern.get('type') in ['BLOCK', 'SWEEP'] and pattern.get('total_volume', 0) > 1000:
                    significance = 'HIGH'
                    break
                elif pattern.get('confidence', 0) > 0.8:
                    significance = 'MEDIUM'
            
            return {
                'activity_level': activity_level,
                'dominant_direction': dominant_direction,
                'significance': significance,
                'recent_pattern_count': pattern_count,
                'pattern_types': pattern_types,
                'total_volume': total_volume
            }
            
        except Exception as e:
            self.logger.error(f"Error creating summary from snapshot data: {e}")
            return {
                'activity_level': 'LOW',
                'dominant_direction': 'NEUTRAL',
                'significance': 'LOW',
                'recent_pattern_count': 0,
                'error': str(e)
            }
    
    def _create_global_summary_from_snapshot(self, summary: Dict[str, Any], patterns: List[Dict[str, Any]], contracts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Create global summary from snapshot data"""
        try:
            # Use snapshot summary if available
            if summary:
                hot_contracts = summary.get('hot_contracts', [])
                active_strikes = []
                
                for hot in hot_contracts[:10]:  # Top 10
                    active_strikes.append({
                        'symbol': hot.get('symbol', ''),
                        'volume': hot.get('volume', 0),
                        'pattern_count': hot.get('pattern_count', 0),
                        'activity_score': hot.get('activity_score', 0)
                    })
                
                # Determine institutional bias from summary
                call_volume = summary.get('call_volume', 0)
                put_volume = summary.get('put_volume', 0)
                dominant_flow = summary.get('dominant_flow', 'NEUTRAL')
                
                institutional_bias = {
                    'direction': dominant_flow,
                    'confidence': 0.8 if dominant_flow != 'NEUTRAL' else 0.5,
                    'call_volume': call_volume,
                    'put_volume': put_volume,
                    'put_call_ratio': summary.get('put_call_ratio', 0)
                }
                
                return {
                    'most_active_strikes': active_strikes,
                    'institutional_bias': institutional_bias,
                    'total_contracts_monitored': summary.get('total_contracts_monitored', 0),
                    'active_patterns': summary.get('active_patterns', 0),
                    'sweep_patterns': summary.get('sweep_patterns', 0),
                    'block_patterns': summary.get('block_patterns', 0),
                    'unusual_volume_patterns': summary.get('unusual_volume_patterns', 0)
                }
            
            # Fallback to creating summary from contracts if no snapshot summary
            return self._create_global_summary(contracts, contracts[0].get('ticker', '') if contracts else '')
            
        except Exception as e:
            self.logger.error(f"Error creating global summary from snapshot: {e}")
            return {}

# Legacy methods removed - all functionality now uses gRPC snapshot-based approach

    def _create_global_summary(self, contracts: List[Dict[str, Any]], ticker: str) -> Dict[str, Any]:
        """
        Create global summary across all contracts
        """
        if not contracts:
            return {}

        # Find most active strikes
        active_strikes = []
        for contract in contracts:
            state = contract.get('current_state', {})
            activity_level = state.get('activity_level', 'LOW')

            # Only include high activity contracts
            if activity_level in ['HIGH', 'VERY_HIGH']:
                active_strikes.append({
                    'price': contract.get('strike_display'),
                    'option_type': contract.get('option_type'),
                    'activity_level': activity_level
                })

        # Sort by activity level
        active_strikes.sort(key=lambda x: 0 if x['activity_level'] == 'VERY_HIGH' else 1)
        active_strikes = active_strikes[:10]  # Top 10

        # Determine institutional bias
        institutional_bias = self._calculate_institutional_bias(contracts)

        # Detect recent trend
        recent_trend = self._detect_recent_trend(contracts)

        return {
            'most_active_strikes': active_strikes,
            'institutional_bias': institutional_bias,
            'recent_trend': recent_trend
        }

    def _calculate_institutional_bias(self, contracts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate institutional bias from contract activity"""
        # Count directional signals
        call_bullish_count = sum(1 for c in contracts
                                 if c.get('option_type') == 'C' and
                                 c.get('current_state', {}).get('dominant_direction', '') in ['BUY', 'STRONG_BUY'])

        call_bearish_count = sum(1 for c in contracts
                                 if c.get('option_type') == 'C' and
                                 c.get('current_state', {}).get('dominant_direction', '') in ['SELL', 'STRONG_SELL'])

        put_bullish_count = sum(1 for c in contracts
                                if c.get('option_type') == 'P' and
                                c.get('current_state', {}).get('dominant_direction', '') in ['SELL', 'STRONG_SELL'])

        put_bearish_count = sum(1 for c in contracts
                                if c.get('option_type') == 'P' and
                                c.get('current_state', {}).get('dominant_direction', '') in ['BUY', 'STRONG_BUY'])

        # Calculate overall bias
        bullish_signals = call_bullish_count + put_bullish_count
        bearish_signals = call_bearish_count + put_bearish_count

        if bullish_signals > bearish_signals * 2:
            direction = 'STRONGLY_BULLISH'
            confidence = 0.9
        elif bullish_signals > bearish_signals:
            direction = 'BULLISH'
            confidence = 0.7
        elif bearish_signals > bullish_signals * 2:
            direction = 'STRONGLY_BEARISH'
            confidence = 0.9
        elif bearish_signals > bullish_signals:
            direction = 'BEARISH'
            confidence = 0.7
        else:
            direction = 'NEUTRAL'
            confidence = 0.5

        # Find primary contracts
        primary_contracts = self._find_primary_contracts(contracts, direction)

        return {
            'direction': direction,
            'confidence': confidence,
            'primary_contracts': primary_contracts[:5]  # Top 5
        }

    def _find_primary_contracts(self, contracts: List[Dict[str, Any]], direction: str) -> List[Dict[str, Any]]:
        """Find primary contracts driving the bias"""
        primary_contracts = []

        if direction in ['BULLISH', 'STRONGLY_BULLISH']:
            # Find bullish contracts
            for c in contracts:
                if ((c.get('option_type') == 'C' and
                     c.get('current_state', {}).get('dominant_direction', '') in ['BUY', 'STRONG_BUY']) or
                    (c.get('option_type') == 'P' and
                     c.get('current_state', {}).get('dominant_direction', '') in ['SELL', 'STRONG_SELL'])):
                    
                    if c.get('current_state', {}).get('activity_level', '') in ['HIGH', 'VERY_HIGH']:
                        primary_contracts.append({
                            'strike': c.get('strike_display'),
                            'option_type': 'CALL' if c.get('option_type') == 'C' else 'PUT',
                            'expiration': self.grpc_client.format_expiration(c.get('expiration', 0))
                        })

        elif direction in ['BEARISH', 'STRONGLY_BEARISH']:
            # Find bearish contracts
            for c in contracts:
                if ((c.get('option_type') == 'P' and
                     c.get('current_state', {}).get('dominant_direction', '') in ['BUY', 'STRONG_BUY']) or
                    (c.get('option_type') == 'C' and
                     c.get('current_state', {}).get('dominant_direction', '') in ['SELL', 'STRONG_SELL'])):
                    
                    if c.get('current_state', {}).get('activity_level', '') in ['HIGH', 'VERY_HIGH']:
                        primary_contracts.append({
                            'strike': c.get('strike_display'),
                            'option_type': 'PUT' if c.get('option_type') == 'P' else 'CALL',
                            'expiration': self.grpc_client.format_expiration(c.get('expiration', 0))
                        })

        return primary_contracts

    def _detect_recent_trend(self, contracts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Detect recent trends across all contracts
        """
        # Collect all transitions
        all_transitions = []

        for contract in contracts:
            historical = contract.get('historical_summary', {})
            transitions = historical.get('key_transitions', [])

            for transition in transitions:
                transition_copy = transition.copy()
                transition_copy['contract'] = {
                    'strike': contract.get('strike_display'),
                    'option_type': contract.get('option_type')
                }
                all_transitions.append(transition_copy)

        if not all_transitions:
            return {}

        # Sort by time (most recent first)
        all_transitions.sort(key=lambda x: x.get('time', ''), reverse=True)

        # Look at the most recent significant transition
        recent_transition = all_transitions[0] if all_transitions else None

        if not recent_transition:
            return {}

        # Create trend description
        trend_description = self._create_trend_description(contracts)

        return {
            'timespan': '30m',
            'description': trend_description,
            'direction_change': {
                'time': recent_transition.get('time', ''),
                'from': recent_transition.get('from', ''),
                'to': recent_transition.get('to', '')
            } if recent_transition else {}
        }

    def _create_trend_description(self, contracts: List[Dict[str, Any]]) -> str:
        """Create human-readable trend description"""
        # Count active contracts by type
        active_calls = sum(1 for c in contracts
                          if c.get('option_type') == 'C' and
                          c.get('current_state', {}).get('activity_level', '') in ['HIGH', 'VERY_HIGH'])
        
        active_puts = sum(1 for c in contracts
                         if c.get('option_type') == 'P' and
                         c.get('current_state', {}).get('activity_level', '') in ['HIGH', 'VERY_HIGH'])

        if active_calls > active_puts:
            return "Increasing call activity with institutional participation"
        elif active_puts > active_calls:
            return "Increasing put activity suggesting defensive positioning"
        elif active_calls > 0 and active_puts > 0:
            return "Mixed options activity across calls and puts"
        else:
            return "Limited options activity detected"

# Method removed - functionality replaced by gRPC snapshot processing
