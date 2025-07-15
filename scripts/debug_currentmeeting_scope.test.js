/**
 * Focused diagnostic test to validate the currentMeeting scope isolation issue
 */

describe('CurrentMeeting Scope Isolation Debug', () => {
  let originalCurrentMeeting;
  
  beforeEach(() => {
    // Clean setup
    global.fetch = jest.fn();
    
    // Reset DOM
    document.head.innerHTML = '';
    document.body.innerHTML = `
      <html class="theme-eink">
        <head><title>CalendarBot</title></head>
        <body>
          <div class="whats-next-content"></div>
          <div class="countdown-time">--</div>
          <div class="countdown-label">Next Meeting</div>
          <div class="countdown-units">Minutes</div>
        </body>
      </html>
    `;
    
    console.log('\n=== SCOPE ISOLATION DEBUG ===');
    
    // Check initial state
    console.log('BEFORE SETTING: window.currentMeeting =', window.currentMeeting);
    
    // Set the test data on window
    window.currentMeeting = { title: 'Test Meeting' };
    window.upcomingMeetings = [{ title: 'Meeting 1' }, { title: 'Meeting 2' }];
    
    console.log('AFTER SETTING: window.currentMeeting =', window.currentMeeting);
    
    // Load the module AFTER setting the data
    require('../calendarbot/web/static/layouts/whats-next-view/whats-next-view.js');
    
    console.log('AFTER REQUIRE: window.currentMeeting =', window.currentMeeting);
    
    // Check if debug interface exists
    if (window.whatsNextView) {
      console.log('DEBUG INTERFACE EXISTS');
      console.log('whatsNextView.getCurrentMeeting() =', window.whatsNextView.getCurrentMeeting());
      console.log('whatsNextView.getUpcomingMeetings() =', window.whatsNextView.getUpcomingMeetings());
    } else {
      console.log('DEBUG INTERFACE NOT FOUND');
    }
    
    // Trigger DOMContentLoaded
    const event = new Event('DOMContentLoaded');
    document.dispatchEvent(event);
    
    console.log('AFTER DOM LOADED: window.currentMeeting =', window.currentMeeting);
    if (window.whatsNextView) {
      console.log('AFTER DOM LOADED: whatsNextView.getCurrentMeeting() =', window.whatsNextView.getCurrentMeeting());
    }
  });

  afterEach(() => {
    jest.clearAllMocks();
    jest.clearAllTimers();
  });

  it('should demonstrate the scope isolation issue', () => {
    // This is the failing scenario
    console.log('\n=== IN TEST ===');
    console.log('window.currentMeeting =', window.currentMeeting);
    console.log('whatsNextView.getCurrentMeeting() =', window.whatsNextView?.getCurrentMeeting());
    
    // The expectation that fails
    const result = window.whatsNextView?.getCurrentMeeting();
    console.log('Test expects:', { title: 'Test Meeting' });
    console.log('Test receives:', result);
    console.log('Are they equal?', JSON.stringify(result) === JSON.stringify({ title: 'Test Meeting' }));
    
    // Show the problem clearly
    expect(window.currentMeeting).toEqual({ title: 'Test Meeting' }); // This should pass
    
    // This is the actual failing assertion - let's see why
    if (result === null) {
      console.log('DIAGNOSIS: Module\'s internal currentMeeting is null, not connected to window.currentMeeting');
    }
  });
  
  it('should show how module variables are independent of window', () => {
    // Set a value on window
    window.testValue = 'window-value';
    
    // Simulate module creating its own variable
    let moduleTestValue = null;
    window.getModuleTestValue = () => moduleTestValue;
    
    console.log('\n=== VARIABLE INDEPENDENCE TEST ===');
    console.log('window.testValue =', window.testValue);
    console.log('getModuleTestValue() =', window.getModuleTestValue());
    console.log('Are they different?', window.testValue !== window.getModuleTestValue());
    
    expect(window.testValue).toBe('window-value');
    expect(window.getModuleTestValue()).toBe(null);
    expect(window.testValue).not.toBe(window.getModuleTestValue());
  });
});