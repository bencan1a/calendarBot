// Good JavaScript file for testing
function goodFunction() {
    console.log('This is a good function for testing');
    return 'success';
}

function testUtility() {
    return {
        status: 'ok',
        message: 'Test utility working'
    };
}

// Export for testing
window.testGood = goodFunction;