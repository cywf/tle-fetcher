import { useState } from 'react';
import { format } from 'date-fns';
import type { PassSummary } from '@/lib/passes';
import SatDetailsModal from './SatDetailsModal';

interface ResultsTableProps {
  passes: PassSummary[];
}

export default function ResultsTable({ passes }: ResultsTableProps) {
  const [selectedCatid, setSelectedCatid] = useState<number | null>(null);
  const [sortField, setSortField] = useState<'firstSeen' | 'maxElevationDeg'>('firstSeen');
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('asc');
  
  const handleSort = (field: 'firstSeen' | 'maxElevationDeg') => {
    if (sortField === field) {
      setSortDirection(prev => prev === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortDirection('asc');
    }
  };
  
  const sortedPasses = [...passes].sort((a, b) => {
    let comparison = 0;
    
    if (sortField === 'firstSeen') {
      comparison = a.firstSeen.getTime() - b.firstSeen.getTime();
    } else if (sortField === 'maxElevationDeg') {
      comparison = a.maxElevationDeg - b.maxElevationDeg;
    }
    
    return sortDirection === 'asc' ? comparison : -comparison;
  });
  
  if (passes.length === 0) {
    return (
      <div className="panel">
        <h2 className="text-2xl font-bold glow-text text-pink-400 mb-4">Results</h2>
        <p className="text-cyan-300 text-center py-8">
          No passes found. Adjust your parameters and try again.
        </p>
      </div>
    );
  }
  
  return (
    <>
      <div className="panel">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-2xl font-bold glow-text text-pink-400">Results</h2>
          <span className="text-cyan-300 text-sm">
            {passes.length} satellite{passes.length !== 1 ? 's' : ''} detected
          </span>
        </div>
        
        <div className="overflow-x-auto">
          <table className="retro-table">
            <thead>
              <tr>
                <th>
                  <button
                    onClick={() => handleSort('firstSeen')}
                    className="flex items-center gap-1 hover:text-pink-200"
                  >
                    CATID
                  </button>
                </th>
                <th>
                  <button
                    onClick={() => handleSort('firstSeen')}
                    className="flex items-center gap-1 hover:text-pink-200"
                  >
                    First Seen
                    {sortField === 'firstSeen' && (
                      <span>{sortDirection === 'asc' ? '↑' : '↓'}</span>
                    )}
                  </button>
                </th>
                <th>Last Seen</th>
                <th>
                  <button
                    onClick={() => handleSort('maxElevationDeg')}
                    className="flex items-center gap-1 hover:text-pink-200"
                  >
                    Max Elev (°)
                    {sortField === 'maxElevationDeg' && (
                      <span>{sortDirection === 'asc' ? '↑' : '↓'}</span>
                    )}
                  </button>
                </th>
                <th>TLE</th>
                <th>Details</th>
              </tr>
            </thead>
            <tbody>
              {sortedPasses.map((pass) => (
                <tr key={pass.catid}>
                  <td className="font-bold seven-segment">{pass.catid}</td>
                  <td className="text-sm">
                    {format(pass.firstSeen, 'yyyy-MM-dd HH:mm:ss')}
                  </td>
                  <td className="text-sm">
                    {format(pass.lastSeen, 'yyyy-MM-dd HH:mm:ss')}
                  </td>
                  <td className="font-bold text-green-400">
                    {pass.maxElevationDeg.toFixed(1)}°
                  </td>
                  <td>
                    <a
                      href={pass.tleUrl}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-pink-400 hover:text-pink-300 underline"
                    >
                      Download
                    </a>
                  </td>
                  <td>
                    <button
                      onClick={() => setSelectedCatid(pass.catid)}
                      className="bg-purple-600 hover:bg-purple-500 text-white px-3 py-1 rounded text-sm font-bold"
                    >
                      DETAILS
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
      
      {selectedCatid && (
        <SatDetailsModal
          catid={selectedCatid}
          onClose={() => setSelectedCatid(null)}
        />
      )}
    </>
  );
}
