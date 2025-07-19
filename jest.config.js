/**
 * @fileoverview Jest configuration for CalendarBot JavaScript testing
 * Clean configuration for 80% coverage target across layout and shared modules
 */

module.exports = {
  // Test environment
  testEnvironment: 'jsdom',
  
  // Test file patterns
  testMatch: [
    '<rootDir>/tests/**/*.test.js'
  ],
  
  // Coverage configuration
  collectCoverage: true,
  collectCoverageFrom: [
    'calendarbot/web/static/shared/js/**/*.js',
    'calendarbot/web/static/layouts/**/*.js',
    '!**/*.min.js',
    '!**/node_modules/**',
    '!**/vendor/**'
  ],
  
  coverageDirectory: 'tests/coverage',
  
  coverageReporters: [
    'text',
    'lcov',
    'html'
  ],
  
  coverageThreshold: {
    global: {
      branches: 60,
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
  
  // Setup files
  setupFilesAfterEnv: [
    '<rootDir>/tests/__tests__/jest-setup.js'
  ],
  
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
    '/tests/.jest-cache/'
  ],
  
  // Custom test environment options
  testEnvironmentOptions: {
    url: 'http://192.168.1.45:8080'
  }
};