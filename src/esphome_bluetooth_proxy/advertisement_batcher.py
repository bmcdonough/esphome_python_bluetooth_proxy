"""Advertisement Batching System.

This module implements efficient batching of BLE advertisements for WiFi transmission,
matching the optimization strategy used in the ESPHome C++ implementation.
"""

import asyncio
import logging
from typing import List, Callable, Optional
import time

from .ble_scanner import BLEAdvertisement

logger = logging.getLogger(__name__)


class AdvertisementBatcher:
    """Batches advertisements for efficient WiFi transmission.
    
    This matches the ESPHome C++ implementation's batching strategy:
    - Batch size of 16 advertisements for optimal WiFi MTU utilization
    - Pre-allocated response objects to minimize memory allocation
    - Advertisement pooling for memory efficiency
    """
    
    # Match ESPHome C++ constants
    FLUSH_BATCH_SIZE = 16  # Optimal batch size for WiFi MTU
    FLUSH_TIMEOUT_MS = 100  # Maximum time to wait before flushing
    
    def __init__(self, send_callback: Callable[[List[BLEAdvertisement]], None]):
        """Initialize advertisement batcher.
        
        Args:
            send_callback: Function to call when batch is ready to send
        """
        self.send_callback = send_callback
        
        # Batching state
        self.advertisement_batch: List[BLEAdvertisement] = []
        self.advertisement_pool: List[BLEAdvertisement] = []
        self.last_flush_time = 0
        
        # Flush timer
        self.flush_timer: Optional[asyncio.TimerHandle] = None
        
        # Pre-allocate batch capacity
        self.advertisement_batch.reserve = self.FLUSH_BATCH_SIZE
        
        logger.debug(f"Advertisement batcher initialized (batch_size={self.FLUSH_BATCH_SIZE})")
    
    def add_advertisement(self, advertisement: BLEAdvertisement) -> None:
        """Add advertisement to batch.
        
        Args:
            advertisement: BLE advertisement to add
        """
        # Add to current batch
        self.advertisement_batch.append(advertisement)
        
        logger.debug(f"Added advertisement from {advertisement.address:012X} "
                    f"(batch size: {len(self.advertisement_batch)}/{self.FLUSH_BATCH_SIZE})")
        
        # Check if we should flush
        if self._should_flush():
            asyncio.create_task(self.flush_batch())
        elif not self.flush_timer:
            # Start flush timer if not already running
            self._start_flush_timer()
    
    def _should_flush(self) -> bool:
        """Check if batch should be flushed.
        
        Returns:
            bool: True if batch should be flushed
        """
        # Flush if batch is full
        if len(self.advertisement_batch) >= self.FLUSH_BATCH_SIZE:
            return True
        
        # Flush if timeout exceeded
        current_time = time.time() * 1000  # Convert to milliseconds
        if (current_time - self.last_flush_time) >= self.FLUSH_TIMEOUT_MS:
            return True
        
        return False
    
    def _start_flush_timer(self) -> None:
        """Start the flush timer."""
        if self.flush_timer:
            self.flush_timer.cancel()
        
        # Calculate timeout
        timeout_seconds = self.FLUSH_TIMEOUT_MS / 1000.0
        
        # Schedule flush
        loop = asyncio.get_event_loop()
        self.flush_timer = loop.call_later(timeout_seconds, self._on_flush_timeout)
    
    def _on_flush_timeout(self) -> None:
        """Handle flush timeout."""
        self.flush_timer = None
        if self.advertisement_batch:
            asyncio.create_task(self.flush_batch())
    
    async def flush_batch(self) -> None:
        """Flush current batch of advertisements."""
        if not self.advertisement_batch:
            return
        
        # Cancel flush timer
        if self.flush_timer:
            self.flush_timer.cancel()
            self.flush_timer = None
        
        # Get current batch
        batch_to_send = self.advertisement_batch.copy()
        batch_size = len(batch_to_send)
        
        # Clear current batch
        self.advertisement_batch.clear()
        
        # Update flush time
        self.last_flush_time = time.time() * 1000
        
        logger.debug(f"Flushing advertisement batch ({batch_size} advertisements)")
        
        try:
            # Send batch via callback
            self.send_callback(batch_to_send)
            
            # Move advertisements to pool for reuse (memory optimization)
            self.advertisement_pool.extend(batch_to_send)
            
            # Limit pool size to prevent memory growth
            if len(self.advertisement_pool) > self.FLUSH_BATCH_SIZE * 2:
                self.advertisement_pool = self.advertisement_pool[-self.FLUSH_BATCH_SIZE:]
            
        except Exception as e:
            logger.error(f"Error sending advertisement batch: {e}")
    
    async def force_flush(self) -> None:
        """Force flush of current batch regardless of size."""
        if self.advertisement_batch:
            logger.debug("Force flushing advertisement batch")
            await self.flush_batch()
    
    def get_batch_size(self) -> int:
        """Get current batch size."""
        return len(self.advertisement_batch)
    
    def get_pool_size(self) -> int:
        """Get advertisement pool size."""
        return len(self.advertisement_pool)
    
    def clear_batch(self) -> None:
        """Clear current batch without sending."""
        if self.flush_timer:
            self.flush_timer.cancel()
            self.flush_timer = None
        
        batch_size = len(self.advertisement_batch)
        self.advertisement_batch.clear()
        
        if batch_size > 0:
            logger.debug(f"Cleared advertisement batch ({batch_size} advertisements)")
    
    def get_stats(self) -> dict:
        """Get batching statistics.
        
        Returns:
            dict: Statistics about batching performance
        """
        return {
            "batch_size": len(self.advertisement_batch),
            "pool_size": len(self.advertisement_pool),
            "max_batch_size": self.FLUSH_BATCH_SIZE,
            "flush_timeout_ms": self.FLUSH_TIMEOUT_MS,
            "last_flush_time": self.last_flush_time,
            "timer_active": self.flush_timer is not None
        }
