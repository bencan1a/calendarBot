#!/usr/bin/env python3
"""
Debug script for countdown display issue in whats-next-view.
Adds comprehensive logging to validate time calculation assumptions.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def add_countdown_debug_logging():
    """Add debug logging to whats-next-view.js to diagnose countdown issue."""

    js_file_path = (
        project_root / "calendarbot/web/static/layouts/whats-next-view/whats-next-view.js"
    )

    if not js_file_path.exists():
        print(f"ERROR: JavaScript file not found at {js_file_path}")
        return False

    # Read current content
    with open(js_file_path) as f:
        content = f.read()

    # Define debug logging to inject
    debug_logging = """
// DEBUG: Enhanced logging for countdown issue
function debugLog(message, data = null) {
    const timestamp = new Date().toISOString();
    if (data) {
        console.log(`[COUNTDOWN_DEBUG ${timestamp}] ${message}:`, data);
    } else {
        console.log(`[COUNTDOWN_DEBUG ${timestamp}] ${message}`);
    }
}

// DEBUG: Override getCurrentTime with logging
const originalGetCurrentTime = getCurrentTime;
function getCurrentTime() {
    const result = originalGetCurrentTime();
    debugLog("getCurrentTime() called", {
        result: result,
        resultType: typeof result,
        isValid: result instanceof Date && !isNaN(result.getTime()),
        backendBaselineTime: backendBaselineTime,
        frontendBaselineTime: frontendBaselineTime
    });
    return result;
}
"""

    # Find the updateCountdown function and add debug logging
    update_countdown_debug = """function updateCountdown() {
    debugLog("=== updateCountdown() called ===");
    
    // Use cached DOM elements for better performance
    if (!DOMCache.countdownTime) {
        DOMCache.countdownTime = document.querySelector('.countdown-time');
        DOMCache.countdownLabel = document.querySelector('.countdown-label');
        DOMCache.countdownUnits = document.querySelector('.countdown-units');
        DOMCache.countdownContainer = document.querySelector('.countdown-container');
    }

    debugLog("DOM elements check", {
        countdownTime: !!DOMCache.countdownTime,
        countdownLabel: !!DOMCache.countdownLabel,
        countdownUnits: !!DOMCache.countdownUnits,
        countdownContainer: !!DOMCache.countdownContainer,
        currentMeeting: !!currentMeeting
    });

    if (!DOMCache.countdownTime || !currentMeeting) {
        debugLog("EARLY EXIT - missing DOM elements or currentMeeting", {
            hasDOMElements: !!DOMCache.countdownTime,
            hasCurrentMeeting: !!currentMeeting,
            currentMeetingData: currentMeeting
        });
        return;
    }

    const now = getCurrentTime();
    const meetingStart = new Date(currentMeeting.start_time);
    const meetingEnd = new Date(currentMeeting.end_time);

    debugLog("Time calculations", {
        now: now,
        nowValid: now instanceof Date && !isNaN(now.getTime()),
        meetingStart: meetingStart,
        meetingStartValid: meetingStart instanceof Date && !isNaN(meetingStart.getTime()),
        meetingEnd: meetingEnd,
        meetingEndValid: meetingEnd instanceof Date && !isNaN(meetingEnd.getTime()),
        currentMeetingStartTime: currentMeeting.start_time,
        currentMeetingEndTime: currentMeeting.end_time
    });

    let timeRemaining;
    let labelText;

    // Determine if meeting is current or upcoming
    if (now >= meetingStart && now <= meetingEnd) {
        // Meeting is happening now - show time until end
        timeRemaining = meetingEnd - now;
        labelText = 'Time Remaining';
        debugLog("Meeting is CURRENT", { timeRemaining, labelText });
    } else if (meetingStart > now) {
        // Meeting is upcoming - show time until start
        timeRemaining = meetingStart - now;
        labelText = 'Starts In';
        debugLog("Meeting is UPCOMING", { timeRemaining, labelText });
    } else {
        // Meeting has passed
        debugLog("Meeting has PASSED - calling detectCurrentMeeting()");
        detectCurrentMeeting();
        return;
    }

    if (timeRemaining <= 0) {
        debugLog("Time remaining <= 0 - calling detectCurrentMeeting()");
        detectCurrentMeeting();
        return;
    }

    // Performance optimization: Calculate time gap efficiently
    const timeGap = calculateTimeGapOptimized(now, meetingStart);
    const boundaryAlert = checkBoundaryAlert(timeGap);

    debugLog("Time gap calculations", {
        timeGap: timeGap,
        boundaryAlert: boundaryAlert
    });

    // Performance optimization: Generate display values
    let displayText;
    let unitsText;

    if (now < meetingStart) {
        // Upcoming meeting - use optimized formatTimeGap function
        const formattedGap = formatTimeGapOptimized(timeGap);
        displayText = formattedGap.number;
        unitsText = formattedGap.units;

        debugLog("Upcoming meeting formatting", {
            formattedGap: formattedGap,
            displayText: displayText,
            unitsText: unitsText
        });

        // Special handling for critical alerts
        if (boundaryAlert.type === 'critical') {
            labelText = boundaryAlert.message;
            unitsText = 'REMAINING';
        } else if (boundaryAlert.type === 'tight') {
            labelText = boundaryAlert.message;
        }
    } else {
        // Meeting in progress - show time remaining in hours:minutes format
        const hours = Math.floor(timeRemaining / (1000 * 60 * 60));
        const minutes = Math.floor((timeRemaining % (1000 * 60 * 60)) / (1000 * 60));

        debugLog("Meeting in progress formatting", {
            hours: hours,
            minutes: minutes,
            timeRemaining: timeRemaining
        });

        if (hours > 0) {
            displayText = `${hours}:${minutes.toString().padStart(2, '0')}`;
            unitsText = hours === 1 ? 'Hour' : 'Hours';
        } else {
            displayText = minutes.toString();
            unitsText = minutes === 1 ? 'Minute' : 'Minutes';
        }
    }

    debugLog("Final display values", {
        displayText: displayText,
        unitsText: unitsText,
        labelText: labelText
    });

    // Performance optimization: Check if values have changed before updating DOM
    const currentCssClass = boundaryAlert.cssClass || '';
    const hasChanges = (
        lastCountdownValues.displayText !== displayText ||
        lastCountdownValues.unitsText !== unitsText ||
        lastCountdownValues.labelText !== labelText ||
        lastCountdownValues.cssClass !== currentCssClass ||
        lastCountdownValues.urgent !== boundaryAlert.urgent
    );

    debugLog("Change detection", {
        hasChanges: hasChanges,
        lastCountdownValues: lastCountdownValues,
        newValues: {
            displayText: displayText,
            unitsText: unitsText,
            labelText: labelText,
            cssClass: currentCssClass,
            urgent: boundaryAlert.urgent
        }
    });

    if (!hasChanges) {
        debugLog("NO CHANGES - skipping DOM updates");
        return;
    }

    // Update DOM only when values have changed (using cached elements)
    if (lastCountdownValues.displayText !== displayText) {
        debugLog("Updating countdown time DOM element", {
            element: DOMCache.countdownTime,
            oldValue: lastCountdownValues.displayText,
            newValue: displayText
        });
        DOMCache.countdownTime.textContent = displayText;
        lastCountdownValues.displayText = displayText;
    }

    if (lastCountdownValues.labelText !== labelText && DOMCache.countdownLabel) {
        debugLog("Updating countdown label DOM element", {
            element: DOMCache.countdownLabel,
            oldValue: lastCountdownValues.labelText,
            newValue: labelText
        });
        DOMCache.countdownLabel.textContent = labelText;
        lastCountdownValues.labelText = labelText;
    }

    if (lastCountdownValues.unitsText !== unitsText && DOMCache.countdownUnits) {
        debugLog("Updating countdown units DOM element", {
            element: DOMCache.countdownUnits,
            oldValue: lastCountdownValues.unitsText,
            newValue: unitsText
        });
        DOMCache.countdownUnits.textContent = unitsText;
        lastCountdownValues.unitsText = unitsText;
    }

    // Update CSS classes only when they change (using cached container)
    if (DOMCache.countdownContainer && lastCountdownValues.cssClass !== currentCssClass) {
        debugLog("Updating CSS classes", {
            oldClass: lastCountdownValues.cssClass,
            newClass: currentCssClass
        });
        // Remove existing time gap classes
        DOMCache.countdownContainer.classList.remove('time-gap-critical', 'time-gap-tight', 'time-gap-comfortable');

        // Add new boundary alert class
        if (boundaryAlert.cssClass) {
            DOMCache.countdownContainer.classList.add(boundaryAlert.cssClass);
        }
        lastCountdownValues.cssClass = currentCssClass;
    }

    // Update urgent class only when it changes (using cached elements)
    if (lastCountdownValues.urgent !== boundaryAlert.urgent) {
        debugLog("Updating urgent classes", {
            oldUrgent: lastCountdownValues.urgent,
            newUrgent: boundaryAlert.urgent
        });
        if (DOMCache.countdownContainer) {
            if (boundaryAlert.urgent) {
                DOMCache.countdownContainer.classList.add('urgent');
            } else {
                DOMCache.countdownContainer.classList.remove('urgent');
            }
        }

        // Legacy urgent support for countdown element
        const isLegacyUrgent = timeRemaining < 15 * 60 * 1000;
        if (isLegacyUrgent) {
            DOMCache.countdownTime.classList.add('urgent');
        } else {
            DOMCache.countdownTime.classList.remove('urgent');
        }

        lastCountdownValues.urgent = boundaryAlert.urgent;
    }

    debugLog("=== updateCountdown() completed successfully ===");

    // P0 Feature: Enhanced boundary alert announcements (unchanged)
    const totalMinutes = Math.floor(timeGap / (1000 * 60));
    if (totalMinutes === 10 || totalMinutes === 5 || totalMinutes === 2 || totalMinutes === 1) {
        const announcement = boundaryAlert.type === 'critical'
            ? `WRAP UP NOW - ${totalMinutes} ${totalMinutes === 1 ? 'minute' : 'minutes'} until ${currentMeeting.title}`
            : `${totalMinutes} ${totalMinutes === 1 ? 'minute' : 'minutes'} until ${currentMeeting.title}`;
        announceToScreenReader(announcement);
    }
}"""

    # Add debug logging to detectCurrentMeeting function
    detect_current_meeting_debug = """function detectCurrentMeeting() {
    debugLog("=== detectCurrentMeeting() called ===");
    
    const now = getCurrentTime();
    debugLog("Current time from getCurrentTime()", {
        now: now,
        nowType: typeof now,
        nowValid: now instanceof Date && !isNaN(now.getTime())
    });
    
    currentMeeting = null;
    debugLog("Reset currentMeeting to null");

    debugLog("upcomingMeetings array", {
        length: upcomingMeetings.length,
        meetings: upcomingMeetings.map(m => ({
            title: m.title,
            start_time: m.start_time,
            end_time: m.end_time,
            graph_id: m.graph_id
        }))
    });

    // Phase 2 Frontend Update: Prioritize upcoming meetings first, current meetings as fallback
    // This ensures frontend and backend select identical meetings consistently
    
    // First pass: Look for upcoming meetings (prioritized)
    debugLog("First pass: Looking for upcoming meetings");
    for (const meeting of upcomingMeetings) {
        const meetingStart = new Date(meeting.start_time);
        
        debugLog("Checking meeting for upcoming", {
            title: meeting.title,
            start_time: meeting.start_time,
            meetingStart: meetingStart,
            meetingStartValid: meetingStart instanceof Date && !isNaN(meetingStart.getTime()),
            isUpcoming: meetingStart > now
        });
        
        // Check if meeting is upcoming
        if (meetingStart > now) {
            currentMeeting = meeting;
            debugLog("FOUND UPCOMING MEETING", { title: meeting.title, start_time: meeting.start_time });
            break;
        }
    }
    
    // Second pass: If no upcoming meetings found, look for current meetings as fallback
    if (!currentMeeting) {
        debugLog("Second pass: Looking for current meetings (fallback)");
        for (const meeting of upcomingMeetings) {
            const meetingStart = new Date(meeting.start_time);
            const meetingEnd = new Date(meeting.end_time);
            
            debugLog("Checking meeting for current", {
                title: meeting.title,
                start_time: meeting.start_time,
                end_time: meeting.end_time,
                meetingStart: meetingStart,
                meetingEnd: meetingEnd,
                isCurrent: now >= meetingStart && now <= meetingEnd
            });
            
            // Check if meeting is currently happening
            if (now >= meetingStart && now <= meetingEnd) {
                currentMeeting = meeting;
                debugLog("FOUND CURRENT MEETING", { title: meeting.title, start_time: meeting.start_time });
                break;
            }
        }
    }

    debugLog("detectCurrentMeeting() result", {
        foundMeeting: !!currentMeeting,
        currentMeetingTitle: currentMeeting ? currentMeeting.title : null,
        currentMeetingStartTime: currentMeeting ? currentMeeting.start_time : null
    });

    updateMeetingDisplayOptimized();
    debugLog("=== detectCurrentMeeting() completed ===");
}"""

    # Inject debug logging at the beginning of the file
    content = content.replace(
        "/* CalendarBot Whats-Next-View Layout JavaScript */",
        f"/* CalendarBot Whats-Next-View Layout JavaScript */\n\n{debug_logging}",
    )

    # Replace the updateCountdown function
    content = content.replace(
        "function updateCountdown() {",
        debug_logging
        + "\n"
        + update_countdown_debug.replace(
            "function updateCountdown() {", "function updateCountdown() {"
        )[20:],  # Remove duplicate function declaration
    )

    # Replace the detectCurrentMeeting function
    old_detect_function = """function detectCurrentMeeting() {
    const now = getCurrentTime();
    currentMeeting = null;

    // Phase 2 Frontend Update: Prioritize upcoming meetings first, current meetings as fallback
    // This ensures frontend and backend select identical meetings consistently
    
    // First pass: Look for upcoming meetings (prioritized)
    for (const meeting of upcomingMeetings) {
        const meetingStart = new Date(meeting.start_time);
        
        // Check if meeting is upcoming
        if (meetingStart > now) {
            currentMeeting = meeting;
            break;
        }
    }
    
    // Second pass: If no upcoming meetings found, look for current meetings as fallback
    if (!currentMeeting) {
        for (const meeting of upcomingMeetings) {
            const meetingStart = new Date(meeting.start_time);
            const meetingEnd = new Date(meeting.end_time);
            
            // Check if meeting is currently happening
            if (now >= meetingStart && now <= meetingEnd) {
                currentMeeting = meeting;
                break;
            }
        }
    }

    updateMeetingDisplayOptimized();
}"""

    content = content.replace(old_detect_function, detect_current_meeting_debug)

    # Write the modified content back
    with open(js_file_path, "w") as f:
        f.write(content)

    print(f"✅ Added debug logging to {js_file_path}")
    print("\nDebug logging added for:")
    print("  - getCurrentTime() function calls")
    print("  - updateCountdown() function execution")
    print("  - detectCurrentMeeting() function execution")
    print("  - DOM element selection and updates")
    print("  - Time calculations and formatting")
    print("\nTo see debug output:")
    print("  1. Run: calendarbot --web --port 8000")
    print("  2. Open browser to http://localhost:8000")
    print("  3. Open browser developer console (F12)")
    print("  4. Look for [COUNTDOWN_DEBUG] messages")

    return True


if __name__ == "__main__":
    print("🔍 Adding debug logging for countdown display issue...")
    success = add_countdown_debug_logging()
    if success:
        print("\n✅ Debug logging setup complete!")
        print("\nNext steps:")
        print("1. Run the app and check browser console for debug output")
        print("2. Look for specific failure points in the logs")
        print("3. Report findings to confirm diagnosis")
    else:
        print("\n❌ Failed to add debug logging")
        sys.exit(1)
