/**
 * Time utilities for parsing, validation, and UTC conversion
 */

import { parse, format, isValid } from 'date-fns';
import { toZonedTime, fromZonedTime } from 'date-fns-tz';

// Cache the default timezone to avoid repeated lookups
const DEFAULT_TIMEZONE = Intl.DateTimeFormat().resolvedOptions().timeZone;

export interface TimeInput {
  date: string;       // YYYY-MM-DD
  time: string;       // HH:mm
  useUTC: boolean;
  timezone?: string;
}

export function parseDateTime(input: TimeInput): Date | null {
  try {
    const dateTimeStr = `${input.date} ${input.time}`;
    const parsed = parse(dateTimeStr, 'yyyy-MM-dd HH:mm', new Date());
    
    if (!isValid(parsed)) {
      return null;
    }

    if (input.useUTC) {
      return parsed;
    }

    // Convert from local timezone to UTC
    const timezone = input.timezone || DEFAULT_TIMEZONE;
    return fromZonedTime(parsed, timezone);
  } catch (error) {
    console.error('Error parsing date/time:', error);
    return null;
  }
}

export function formatDateTime(date: Date, useUTC: boolean = false, timezone?: string): string {
  if (useUTC) {
    return format(date, 'yyyy-MM-dd HH:mm:ss') + ' UTC';
  }
  
  const tz = timezone || DEFAULT_TIMEZONE;
  const zonedDate = toZonedTime(date, tz);
  return format(zonedDate, 'yyyy-MM-dd HH:mm:ss');
}

export function validateDateString(dateStr: string): boolean {
  const regex = /^\d{4}-\d{2}-\d{2}$/;
  if (!regex.test(dateStr)) {
    return false;
  }
  
  const date = parse(dateStr, 'yyyy-MM-dd', new Date());
  return isValid(date);
}

export function validateTimeString(timeStr: string): boolean {
  const regex = /^\d{2}:\d{2}$/;
  if (!regex.test(timeStr)) {
    return false;
  }
  
  const [hours, minutes] = timeStr.split(':').map(Number);
  return hours >= 0 && hours < 24 && minutes >= 0 && minutes < 60;
}

export function getCurrentDateTime(): { date: string; time: string } {
  const now = new Date();
  return {
    date: format(now, 'yyyy-MM-dd'),
    time: format(now, 'HH:mm'),
  };
}
