/**
 * @fileoverview Jest configuration for CalendarBot JavaScript testing
 * Clean configuration for 80% coverage target across layout and shared modules
 */

module.exports = {
  // Test environment
  testEnvironment: 'jsdom',
  
  // Test file patterns - looking only in tests/lite directory
  testMatch: [
    '<rootDir>/tests/lite/**/*.test.js',
    '<rootDir>/tests/lite/**/*.spec.js'
  ],
  
  // Coverage configuration - only collect from calendarbot_lite directory
  collectCoverage: true,
  collectCoverageFrom: [
    '<rootDir>/calendarbot_lite/**/*.js',
    '!**/*.min.js',
    '!**/node_modules/**',
    '!**/vendor/**',
    '!**/__pycache__/**',
    '!**/*.py'
  ],
  
  coverageDirectory: 'tests/coverage',
  
  coverageReporters: [
    'text',
    'lcov',
    'html'
  ],
  
  coverageThreshold: {
    global: {
      branches: 55,
      functions: 60,
      lines: 60,
      statements: 60
    }
  },
  
  // Transform configuration
  transform: {
    '^.+\\.js$': 'babel-jest'
  },
  
  // Test timeout
  testTimeout: 10000,
  
  // Clear mocks between tests
  clearMocks: true,
  
  // Setup files - commented out since jest-setup.js is in deprecated tests
  // setupFilesAfterEnv: [
  //   '<rootDir>/tests/lite/jest-setup.js'
  // ],
  
  // Cache directory
  cacheDirectory: './tests/.jest-cache',
  
  // Module file extensions
  moduleFileExtensions: [
    'js',
    'json'
  ],
  
  // Test paths to ignore
  testPathIgnorePatterns: [
    '/node_modules/',
    '/tests/coverage/',
    '/tests/.jest-cache/',
    '/tests/deprecated*/'
  ],
  
  // Custom test environment options
  testEnvironmentOptions: {
    url: 'http://localhost:8080'
  }
};