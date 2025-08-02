// Good JavaScript file #2 for testing
function goodFunction2() {
    console.log('This is good function #2 for testing');
    return 'success';
}

function testUtility2() {
    return {
        status: 'ok',
        message: 'Test utility 2 working'
    };
}

// Export for testing
window.testGood2 = goodFunction2;