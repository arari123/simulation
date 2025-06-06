/**
 * Signal and Variable Type System Constants
 * 
 * This module defines the type system for signals and variables in the simulation.
 * It mirrors the backend SignalType enum for consistency.
 */

export const SignalType = {
  BOOLEAN: 'boolean',
  INTEGER: 'integer'
}

export const SignalTypeLabels = {
  [SignalType.BOOLEAN]: '논리형 (True/False)',
  [SignalType.INTEGER]: '정수형 (숫자)'
}

/**
 * Get default value for a signal type
 * @param {string} type - Signal type
 * @returns {boolean|number} Default value
 */
export function getDefaultValue(type) {
  switch (type) {
    case SignalType.BOOLEAN:
      return false
    case SignalType.INTEGER:
      return 0
    default:
      throw new Error(`Unknown signal type: ${type}`)
  }
}

/**
 * Validate if value matches the signal type
 * @param {string} type - Signal type
 * @param {any} value - Value to validate
 * @returns {boolean} True if valid
 */
export function validateValue(type, value) {
  switch (type) {
    case SignalType.BOOLEAN:
      return typeof value === 'boolean'
    case SignalType.INTEGER:
      return typeof value === 'number' && Number.isInteger(value)
    default:
      return false
  }
}

/**
 * Parse string value to appropriate type
 * @param {string} type - Signal type
 * @param {string} valueStr - String value to parse
 * @returns {boolean|number} Parsed value
 */
export function parseValue(type, valueStr) {
  switch (type) {
    case SignalType.BOOLEAN:
      if (valueStr.toLowerCase() === 'true') return true
      if (valueStr.toLowerCase() === 'false') return false
      throw new Error(`Invalid boolean value: ${valueStr}`)
    
    case SignalType.INTEGER:
      const num = parseInt(valueStr, 10)
      if (isNaN(num)) {
        throw new Error(`Invalid integer value: ${valueStr}`)
      }
      return num
    
    default:
      throw new Error(`Unknown signal type: ${type}`)
  }
}

/**
 * Format value for display
 * @param {string} type - Signal type  
 * @param {any} value - Value to format
 * @returns {string} Formatted value
 */
export function formatValue(type, value) {
  switch (type) {
    case SignalType.BOOLEAN:
      return value ? 'TRUE' : 'FALSE'
    case SignalType.INTEGER:
      return String(value)
    default:
      return String(value)
  }
}

/**
 * Get input component type for signal type
 * @param {string} type - Signal type
 * @returns {string} Input type ('select' or 'number')
 */
export function getInputType(type) {
  switch (type) {
    case SignalType.BOOLEAN:
      return 'select'
    case SignalType.INTEGER:
      return 'number'
    default:
      return 'text'
  }
}

/**
 * Infer type from value
 * @param {any} value - Value to check
 * @returns {string} Inferred type
 */
export function inferType(value) {
  if (typeof value === 'boolean') {
    return SignalType.BOOLEAN
  }
  if (typeof value === 'number' && Number.isInteger(value)) {
    return SignalType.INTEGER
  }
  // Default to boolean for backward compatibility
  return SignalType.BOOLEAN
}