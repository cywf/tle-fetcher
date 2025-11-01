import { useState } from 'react';
import { z } from 'zod';
import { getCurrentDateTime, validateDateString, validateTimeString } from '@/lib/time';

const formSchema = z.object({
  latitude: z.number().min(-90).max(90),
  longitude: z.number().min(-180).max(180),
  date: z.string().refine(validateDateString, 'Invalid date format'),
  time: z.string().refine(validateTimeString, 'Invalid time format'),
  totMinutes: z.number().min(1).max(1440),
  minElevationDeg: z.number().min(0).max(90),
  useUTC: z.boolean(),
  tleSource: z.enum(['local', 'celestrak', 'both']),
});

export type FormData = z.infer<typeof formSchema>;

interface ControlPanelProps {
  onSubmit: (data: FormData) => void;
  isComputing: boolean;
}

export default function ControlPanel({ onSubmit, isComputing }: ControlPanelProps) {
  const defaultDateTime = getCurrentDateTime();
  
  const [formData, setFormData] = useState<FormData>({
    latitude: 0,
    longitude: 0,
    date: defaultDateTime.date,
    time: defaultDateTime.time,
    totMinutes: 15,
    minElevationDeg: 5,
    useUTC: false,
    tleSource: 'both',
  });
  
  const [errors, setErrors] = useState<Record<string, string>>({});
  
  const handleChange = (field: keyof FormData, value: any) => {
    setFormData(prev => ({
      ...prev,
      [field]: value,
    }));
    
    // Clear error for this field
    if (errors[field]) {
      setErrors(prev => {
        const newErrors = { ...prev };
        delete newErrors[field];
        return newErrors;
      });
    }
  };
  
  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    
    // Validate
    try {
      const validated = formSchema.parse(formData);
      setErrors({});
      onSubmit(validated);
    } catch (error) {
      if (error instanceof z.ZodError) {
        const newErrors: Record<string, string> = {};
        error.errors.forEach(err => {
          if (err.path[0]) {
            newErrors[err.path[0].toString()] = err.message;
          }
        });
        setErrors(newErrors);
      }
    }
  };
  
  return (
    <div className="panel">
      <div className="flex items-center gap-3 mb-6">
        <div className={`led ${isComputing ? 'led-active bg-green-400' : 'bg-gray-600'}`}></div>
        <h2 className="text-2xl font-bold glow-text text-pink-400">Control Panel</h2>
      </div>
      
      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-bold text-cyan-300 mb-1">
              Latitude (°)
            </label>
            <input
              type="number"
              step="0.000001"
              min="-90"
              max="90"
              value={formData.latitude}
              onChange={(e) => handleChange('latitude', parseFloat(e.target.value) || 0)}
              placeholder="-90 to 90"
              disabled={isComputing}
            />
            {errors.latitude && <p className="error-text">{errors.latitude}</p>}
          </div>
          
          <div>
            <label className="block text-sm font-bold text-cyan-300 mb-1">
              Longitude (°)
            </label>
            <input
              type="number"
              step="0.000001"
              min="-180"
              max="180"
              value={formData.longitude}
              onChange={(e) => handleChange('longitude', parseFloat(e.target.value) || 0)}
              placeholder="-180 to 180"
              disabled={isComputing}
            />
            {errors.longitude && <p className="error-text">{errors.longitude}</p>}
          </div>
        </div>
        
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-bold text-cyan-300 mb-1">
              Date
            </label>
            <input
              type="date"
              value={formData.date}
              onChange={(e) => handleChange('date', e.target.value)}
              disabled={isComputing}
            />
            {errors.date && <p className="error-text">{errors.date}</p>}
          </div>
          
          <div>
            <label className="block text-sm font-bold text-cyan-300 mb-1">
              Time
            </label>
            <input
              type="time"
              value={formData.time}
              onChange={(e) => handleChange('time', e.target.value)}
              disabled={isComputing}
            />
            {errors.time && <p className="error-text">{errors.time}</p>}
          </div>
        </div>
        
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-bold text-cyan-300 mb-1">
              Time-on-Target (minutes)
            </label>
            <input
              type="number"
              min="1"
              max="1440"
              value={formData.totMinutes}
              onChange={(e) => handleChange('totMinutes', parseInt(e.target.value) || 15)}
              disabled={isComputing}
            />
            {errors.totMinutes && <p className="error-text">{errors.totMinutes}</p>}
          </div>
          
          <div>
            <label className="block text-sm font-bold text-cyan-300 mb-1">
              Min Elevation (°)
            </label>
            <input
              type="number"
              min="0"
              max="90"
              step="0.1"
              value={formData.minElevationDeg}
              onChange={(e) => handleChange('minElevationDeg', parseFloat(e.target.value) || 5)}
              disabled={isComputing}
            />
            {errors.minElevationDeg && <p className="error-text">{errors.minElevationDeg}</p>}
          </div>
        </div>
        
        <div>
          <label className="block text-sm font-bold text-cyan-300 mb-1">
            TLE Source
          </label>
          <select
            value={formData.tleSource}
            onChange={(e) => handleChange('tleSource', e.target.value)}
            disabled={isComputing}
            className="w-full"
          >
            <option value="both">Local Assets (fallback to CelesTrak)</option>
            <option value="local">Local Assets Only</option>
            <option value="celestrak">CelesTrak Only</option>
          </select>
        </div>
        
        <div className="flex items-center gap-2">
          <input
            type="checkbox"
            id="useUTC"
            checked={formData.useUTC}
            onChange={(e) => handleChange('useUTC', e.target.checked)}
            disabled={isComputing}
            className="w-4 h-4"
          />
          <label htmlFor="useUTC" className="text-sm text-cyan-300">
            Use UTC time (otherwise local time)
          </label>
        </div>
        
        <button
          type="submit"
          disabled={isComputing}
          className="btn-retro w-full disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isComputing ? (
            <span className="flex items-center justify-center gap-2">
              <div className="spinner"></div>
              COMPUTING...
            </span>
          ) : (
            'COMPUTE PASSES'
          )}
        </button>
      </form>
    </div>
  );
}
