// Bad JavaScript file for testing error handling
function badFunction() {
    console.error('This is a bad function for testing');
    throw new Error('Intentional error for testing');
}

// Simulate problematic code
window.badGlobal = 'error-test';