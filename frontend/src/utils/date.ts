import dayjs from 'dayjs';
import relativeTime from 'dayjs/plugin/relativeTime';

dayjs.extend(relativeTime);

/**
 * Format a date string or Date object to a readable format
 * @param date - Date string or Date object
 * @param format - Format string (default: "DD MMM YYYY")
 * @returns Formatted date string
 */
export const formatDate = (date: string | Date | undefined, format = 'DD MMM YYYY'): string => {
  if (!date) return '';
  return dayjs(date).format(format);
};

/**
 * Format a datetime to include time
 * @param date - Date string or Date object
 * @returns Formatted datetime string (DD MMM YYYY, HH:mm)
 */
export const formatDateTime = (date: string | Date | undefined): string => {
  if (!date) return '';
  return dayjs(date).format('DD MMM YYYY, HH:mm');
};

/**
 * Format time only
 * @param date - Date string or Date object
 * @returns Formatted time string (HH:mm)
 */
export const formatTime = (date: string | Date | undefined): string => {
  if (!date) return '';
  return dayjs(date).format('HH:mm');
};

/**
 * Check if a date is in the past
 * @param date - Date string or Date object
 * @returns boolean
 */
export const isPastDate = (date: string | Date): boolean => {
  return dayjs(date).isBefore(dayjs(), 'day');
};

/**
 * Check if a date is today
 * @param date - Date string or Date object
 * @returns boolean
 */
export const isToday = (date: string | Date): boolean => {
  return dayjs(date).isSame(dayjs(), 'day');
};

/**
 * Get relative time from now (e.g., "2 hours ago", "in 3 days")
 * @param date - Date string or Date object
 * @returns Relative time string
 */
export const getRelativeTime = (date: string | Date | undefined): string => {
  if (!date) return '';
  return dayjs(date).fromNow();
};

/**
 * Parse a date string safely
 * @param date - Date string
 * @returns dayjs object or null if invalid
 */
export const parseDate = (date: string) => {
  const parsed = dayjs(date);
  return parsed.isValid() ? parsed : null;
};
