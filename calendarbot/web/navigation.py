"""Web navigation handler integrating with existing navigation system."""

import logging
from datetime import date
from typing import Optional, Dict, Any

from ..ui.navigation import NavigationState

logger = logging.getLogger(__name__)


class WebNavigationHandler:
    """Handles web-based navigation integration with existing navigation system."""
    
    def __init__(self, navigation_state: Optional[NavigationState] = None):
        """Initialize web navigation handler.
        
        Args:
            navigation_state: Optional existing navigation state to use
        """
        self.navigation_state = navigation_state or NavigationState()
        
        # Track navigation state for web interface
        self._navigation_callbacks = []
        
        # Setup navigation state callbacks
        self.navigation_state.add_change_callback(self._on_navigation_changed)
        
        logger.debug("Web navigation handler initialized")
    
    def handle_navigation_action(self, action: str) -> bool:
        """Handle navigation action from web interface.
        
        Args:
            action: Navigation action (prev, next, today, etc.)
            
        Returns:
            True if action was successful
        """
        try:
            old_date = self.navigation_state.selected_date
            
            if action == "prev":
                self.navigation_state.navigate_backward()
            elif action == "next":
                self.navigation_state.navigate_forward()
            elif action == "today":
                self.navigation_state.jump_to_today()
            elif action == "week-start":
                self.navigation_state.jump_to_start_of_week()
            elif action == "week-end":
                self.navigation_state.jump_to_end_of_week()
            else:
                logger.warning(f"Unknown navigation action: {action}")
                return False
            
            new_date = self.navigation_state.selected_date
            logger.debug(f"Web navigation: {action} - {old_date} → {new_date}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error handling navigation action '{action}': {e}")
            return False
    
    def jump_to_date(self, target_date: date) -> bool:
        """Jump to a specific date.
        
        Args:
            target_date: Date to jump to
            
        Returns:
            True if successful
        """
        try:
            old_date = self.navigation_state.selected_date
            self.navigation_state.jump_to_date(target_date)
            new_date = self.navigation_state.selected_date
            
            logger.debug(f"Web navigation: jump to date - {old_date} → {new_date}")
            return True
            
        except Exception as e:
            logger.error(f"Error jumping to date {target_date}: {e}")
            return False
    
    def get_navigation_info(self) -> Dict[str, Any]:
        """Get current navigation information for web display.
        
        Returns:
            Navigation information dictionary
        """
        try:
            return {
                'selected_date': self.navigation_state.get_display_date(),
                'selected_date_iso': self.navigation_state.selected_date.isoformat(),
                'is_today': self.navigation_state.is_today(),
                'is_past': self.navigation_state.is_past(),
                'is_future': self.navigation_state.is_future(),
                'days_from_today': self.navigation_state.days_from_today(),
                'relative_description': self.navigation_state.get_relative_description(),
                'week_context': self.navigation_state.get_week_context(),
                'formatted_date': self.navigation_state.get_formatted_date(),
                'navigation_help': self._get_web_navigation_help()
            }
        except Exception as e:
            logger.error(f"Error getting navigation info: {e}")
            return {
                'selected_date': 'Error',
                'selected_date_iso': date.today().isoformat(),
                'is_today': True,
                'error': str(e)
            }
    
    def _get_web_navigation_help(self) -> str:
        """Get web-specific navigation help text.
        
        Returns:
            Navigation help string
        """
        return "← → Navigate | Space: Today | Home/End: Week | R: Refresh | T: Theme"
    
    def add_navigation_callback(self, callback):
        """Add callback for navigation changes.
        
        Args:
            callback: Function to call when navigation changes
        """
        self._navigation_callbacks.append(callback)
        logger.debug("Added web navigation callback")
    
    def remove_navigation_callback(self, callback):
        """Remove navigation callback.
        
        Args:
            callback: Callback function to remove
        """
        if callback in self._navigation_callbacks:
            self._navigation_callbacks.remove(callback)
            logger.debug("Removed web navigation callback")
    
    def _on_navigation_changed(self, new_date: date):
        """Handle navigation state changes.
        
        Args:
            new_date: New selected date
        """
        logger.debug(f"Web navigation state changed to: {new_date}")
        
        # Notify web-specific callbacks
        for callback in self._navigation_callbacks:
            try:
                callback(new_date, self.get_navigation_info())
            except Exception as e:
                logger.error(f"Error in web navigation callback: {e}")
    
    @property
    def selected_date(self) -> date:
        """Get currently selected date."""
        return self.navigation_state.selected_date
    
    @property
    def today(self) -> date:
        """Get today's date."""
        return self.navigation_state.today
    
    def is_today(self) -> bool:
        """Check if selected date is today."""
        return self.navigation_state.is_today()
    
    def is_past(self) -> bool:
        """Check if selected date is in the past."""
        return self.navigation_state.is_past()
    
    def is_future(self) -> bool:
        """Check if selected date is in the future."""
        return self.navigation_state.is_future()
    
    def get_relative_description(self) -> str:
        """Get relative description of selected date."""
        return self.navigation_state.get_relative_description()
    
    def get_display_date(self) -> str:
        """Get display-friendly date string."""
        return self.navigation_state.get_display_date()
    
    def update_today(self):
        """Update the reference to today's date."""
        self.navigation_state.update_today()