/**
 * Jest configuration for CalendarBot JavaScript testing
 * Tests the web interface JavaScript files for calendar layouts
 */
module.exports = {
  // Test environment
  testEnvironment: 'jsdom',
  
  // Test file patterns
  testMatch: [
    '**/tests/__tests__/**/*.test.{js,jsx}',
    '**/__tests__/**/*.{js,jsx}',
    '**/*.test.{js,jsx}'
  ],

  // Setup files
  setupFilesAfterEnv: ['<rootDir>/tests/__tests__/setup.test.js'],

  // Module file extensions
  moduleFileExtensions: ['js', 'jsx', 'json'],

  // Transform configuration (if needed for ES6+ features)
  transform: {
    '^.+\\.(js|jsx)$': 'babel-jest'
  },

  // Module name mapping for static files and styles
  moduleNameMapper: {
    '\\.(css|less|scss|sass)$': 'identity-obj-proxy',
    '\\.(gif|ttf|eot|svg|png|jpg|jpeg)$': '<rootDir>/tests/__mocks__/fileMock.js'
  },

  // Coverage configuration
  collectCoverage: true,
  coverageDirectory: 'coverage'

  // Global setup/teardown if needed
  // globalSetup: '<rootDir>/tests/__tests__/globalSetup.js',
  // globalTeardown: '<rootDir>/tests/__tests__/globalTeardown.js'
};