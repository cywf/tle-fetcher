/**
 * Satellite pass (LOS) computation using satellite.js (SGP4)
 */

import * as satellite from 'satellite.js';
import type { TLEData } from './tle';

// Type augmentation for missing satellite.js types
declare module 'satellite.js' {
  export function radiansToDegrees(radians: number): number;
  export function degreesToRadians(degrees: number): number;
}

export interface ObserverLocation {
  latitude: number;    // degrees, -90 to 90
  longitude: number;   // degrees, -180 to 180
  altitude?: number;   // meters above sea level, default 0
}

export interface PassSummary {
  catid: number;
  firstSeen: Date;
  lastSeen: Date;
  maxElevationDeg: number;
  tleUrl: string;
}

export interface PassComputeOptions {
  observer: ObserverLocation;
  startTime: Date;
  durationMinutes: number;
  minElevationDeg?: number;  // default 5
  timeStepSec?: number;      // default 10
}

interface LookAngle {
  elevation: number;  // degrees
  azimuth: number;    // degrees
  range: number;      // km
}

/**
 * Convert geodetic coordinates to ECEF
 */
function observerECF(observer: ObserverLocation, date: Date) {
  const gmst = satellite.gstime(date);
  const positionGd = {
    latitude: satellite.degreesToRadians(observer.latitude),
    longitude: satellite.degreesToRadians(observer.longitude),
    height: (observer.altitude || 0) / 1000, // convert to km
  };
  
  return satellite.geodeticToEcf(positionGd);
}

/**
 * Compute look angles from observer to satellite
 */
function getLookAngles(
  satelliteECF: satellite.EcfVec3<number>,
  observerECF: satellite.EcfVec3<number>,
  observer: ObserverLocation,
  date: Date
): LookAngle {
  const positionGd = {
    latitude: satellite.degreesToRadians(observer.latitude),
    longitude: satellite.degreesToRadians(observer.longitude),
    height: (observer.altitude || 0) / 1000,
  };
  
  const lookAngles = satellite.ecfToLookAngles(positionGd, satelliteECF);
  
  return {
    elevation: satellite.radiansToDegrees(lookAngles.elevation),
    azimuth: satellite.radiansToDegrees(lookAngles.azimuth),
    range: lookAngles.rangeSat,
  };
}

/**
 * Compute satellite passes for given TLE and observer
 */
export function computePasses(
  tle: TLEData,
  options: PassComputeOptions
): PassSummary | null {
  const {
    observer,
    startTime,
    durationMinutes,
    minElevationDeg = 5,
    timeStepSec = 10,
  } = options;
  
  // Parse TLE
  const satrec = satellite.twoline2satrec(tle.line1, tle.line2);
  
  if (satrec.error !== 0) {
    console.warn(`Failed to parse TLE for CATID ${tle.catid}`);
    return null;
  }
  
  const endTime = new Date(startTime.getTime() + durationMinutes * 60 * 1000);
  const numSteps = Math.floor((durationMinutes * 60) / timeStepSec);
  
  let inPass = false;
  let passStart: Date | null = null;
  let passEnd: Date | null = null;
  let maxElevation = -90;
  let hasAnyPass = false;
  
  // Propagate through time window
  for (let step = 0; step <= numSteps; step++) {
    const time = new Date(startTime.getTime() + step * timeStepSec * 1000);
    
    // Propagate satellite position
    const positionAndVelocity = satellite.propagate(satrec, time);
    
    if (typeof positionAndVelocity.position === 'boolean') {
      continue; // Propagation failed
    }
    
    const positionEci = positionAndVelocity.position as satellite.EciVec3<number>;
    
    // Convert to ECF
    const gmst = satellite.gstime(time);
    const positionEcf = satellite.eciToEcf(positionEci, gmst);
    
    // Get observer position
    const observerEcfPos = observerECF(observer, time);
    
    // Compute look angles
    const lookAngles = getLookAngles(positionEcf, observerEcfPos, observer, time);
    
    // Check if satellite is above horizon
    if (lookAngles.elevation >= minElevationDeg) {
      if (!inPass) {
        // Start of a pass
        inPass = true;
        passStart = time;
        hasAnyPass = true;
      }
      
      if (lookAngles.elevation > maxElevation) {
        maxElevation = lookAngles.elevation;
      }
      
      passEnd = time;
    } else {
      if (inPass) {
        // End of a pass
        inPass = false;
      }
    }
  }
  
  // If no passes detected, return null
  if (!hasAnyPass || !passStart || !passEnd) {
    return null;
  }
  
  return {
    catid: tle.catid,
    firstSeen: passStart,
    lastSeen: passEnd,
    maxElevationDeg: maxElevation,
    tleUrl: '', // Will be filled by caller
  };
}

/**
 * Compute passes for multiple satellites
 */
export function computeMultiplePasses(
  tles: Map<number, TLEData>,
  options: PassComputeOptions,
  getTLEUrl: (catid: number, source: 'local' | 'celestrak') => string
): PassSummary[] {
  const passes: PassSummary[] = [];
  
  for (const [catid, tle] of tles.entries()) {
    const pass = computePasses(tle, options);
    if (pass) {
      pass.tleUrl = getTLEUrl(catid, tle.source);
      passes.push(pass);
    }
  }
  
  // Sort by first seen time
  passes.sort((a, b) => a.firstSeen.getTime() - b.firstSeen.getTime());
  
  return passes;
}

/**
 * Validate observer coordinates
 */
export function validateObserver(observer: ObserverLocation): string[] {
  const errors: string[] = [];
  
  if (observer.latitude < -90 || observer.latitude > 90) {
    errors.push('Latitude must be between -90 and 90 degrees');
  }
  
  if (observer.longitude < -180 || observer.longitude > 180) {
    errors.push('Longitude must be between -180 and 180 degrees');
  }
  
  if (observer.altitude !== undefined && observer.altitude < 0) {
    errors.push('Altitude must be non-negative');
  }
  
  return errors;
}
