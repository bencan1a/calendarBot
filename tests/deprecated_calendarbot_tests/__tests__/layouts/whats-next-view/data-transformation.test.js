/**
 * @fileoverview Jest Tests - Data Transformation Functions
 * Tests only functions that actually exist in whats-next-view.js implementation
 */

// Import real whats-next-view.js source file
require('../../../../calendarbot/web/static/layouts/whats-next-view/whats-next-view.js');

describe('WhatsNextView Data Transformation', () => {

  beforeEach(() => {
    // Setup basic DOM
    document.body.innerHTML = '<div class="calendar-content"></div>';
  });

  afterEach(() => {
    jest.clearAllMocks();
    document.body.innerHTML = '';
  });

  describe('formatLastUpdate', () => {
    it('should return formatted time string', () => {
      expect(typeof window.formatLastUpdate).toBe('function');
      const result = window.formatLastUpdate();
      expect(typeof result).toBe('string');
      expect(result.length).toBeGreaterThan(0);
    });

    it('should handle null lastDataUpdate', () => {
      const originalLastDataUpdate = window.lastDataUpdate;
      window.lastDataUpdate = null;

      const result = window.formatLastUpdate();
      expect(result).toBe('Just now');

      window.lastDataUpdate = originalLastDataUpdate;
    });
  });

  describe('formatMeetingTime', () => {
    it('should format meeting times correctly', () => {
      expect(typeof window.formatMeetingTime).toBe('function');

      const startTime = '2023-07-19T10:00:00';
      const endTime = '2023-07-19T11:00:00';

      const result = window.formatMeetingTime(startTime, endTime);
      expect(typeof result).toBe('string');
      expect(result).toContain(' - ');
    });

    it('should use formatted time range when provided', () => {
      const startTime = '2023-07-19T10:00:00';
      const endTime = '2023-07-19T11:00:00';
      const formattedTimeRange = '10:00 AM - 11:00 AM';

      const result = window.formatMeetingTime(startTime, endTime, formattedTimeRange);
      expect(result).toBe(formattedTimeRange);
    });
  });

  describe('escapeHtml', () => {
    it('should escape dangerous HTML characters', () => {
      expect(typeof window.escapeHtml).toBe('function');

      const dangerous = '<script>alert("xss")</script>';
      const escaped = window.escapeHtml(dangerous);

      expect(escaped).not.toContain('<script>');
      expect(escaped).toContain('&lt;script&gt;');
    });

    it('should handle various special characters', () => {
      const input = `<>&"'`;
      const expected = `&lt;&gt;&amp;&quot;&#039;`;
      const result = window.escapeHtml(input);

      expect(result).toBe(expected);
    });
  });

  describe('getCurrentTime', () => {
    it('should return current time as Date object', () => {
      expect(typeof window.getCurrentTime).toBe('function');
      const result = window.getCurrentTime();
      expect(result).toBeInstanceOf(Date);
    });

    it('should return valid date', () => {
      const result = window.getCurrentTime();
      expect(result.getTime()).toBeGreaterThan(0);
    });
  });
});