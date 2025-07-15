/**
 * Debug script to diagnose variable scope isolation in Jest tests
 * This will help validate whether the issue is scope isolation vs other causes
 */

// Add diagnostic logging to understand variable scope issues
console.log('=== VARIABLE SCOPE DIAGNOSTIC ===');

// Test 1: Check if window and module variables are different
console.log('\n=== TEST 1: Variable Independence ===');
console.log('Setting window.testVar = "window-value"');
window.testVar = "window-value";

let moduleVar = null;
console.log('Module variable moduleVar:', moduleVar);
console.log('Window variable window.testVar:', window.testVar);
console.log('Are they different?', moduleVar !== window.testVar);

// Test 2: Simulate the currentMeeting scenario
console.log('\n=== TEST 2: Current Meeting Scenario ===');

// This simulates what the test does
window.currentMeeting = { title: 'Test Meeting' };
console.log('Set window.currentMeeting:', window.currentMeeting);

// This simulates what the module's debug interface does
let currentMeeting = null; // Module-scoped variable
const getCurrentMeeting = () => currentMeeting;

console.log('Module getCurrentMeeting() returns:', getCurrentMeeting());
console.log('Window currentMeeting is:', window.currentMeeting);
console.log('Are they the same?', getCurrentMeeting() === window.currentMeeting);

// Test 3: Check if module loading affects scope
console.log('\n=== TEST 3: Module Loading Impact ===');
window.beforeRequireVar = 'set-before';
console.log('Set window.beforeRequireVar:', window.beforeRequireVar);

// Simulate require() behavior
(function() {
  console.log('Inside module scope - window.beforeRequireVar:', window.beforeRequireVar);
  let moduleLocal = 'module-scoped';
  window.getModuleLocal = () => moduleLocal;
  console.log('Created module-scoped variable and getter');
})();

console.log('After module load - window.beforeRequireVar:', window.beforeRequireVar);
console.log('Module local via getter:', window.getModuleLocal());

// Test 4: Event listener timing
console.log('\n=== TEST 4: Event Listener Timing ===');
let initializationCount = 0;
document.addEventListener('DOMContentLoaded', function() {
  initializationCount++;
  console.log('DOMContentLoaded fired, count:', initializationCount);
});

// Manually dispatch to see what happens
const event = new Event('DOMContentLoaded');
document.dispatchEvent(event);