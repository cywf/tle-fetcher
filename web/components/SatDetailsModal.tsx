import { useState, useEffect, Fragment } from 'react';
import { Dialog, Transition } from '@headlessui/react';
import { fetchMetadata, type SatelliteMetadata } from '@/lib/metadata';

interface SatDetailsModalProps {
  catid: number;
  onClose: () => void;
}

export default function SatDetailsModal({ catid, onClose }: SatDetailsModalProps) {
  const [metadata, setMetadata] = useState<SatelliteMetadata | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  useEffect(() => {
    async function loadMetadata() {
      setLoading(true);
      setError(null);
      
      try {
        const data = await fetchMetadata(catid);
        setMetadata(data);
      } catch (err) {
        setError('Failed to load satellite metadata');
        console.error('Metadata fetch error:', err);
      } finally {
        setLoading(false);
      }
    }
    
    loadMetadata();
  }, [catid]);
  
  return (
    <Transition appear show={true} as={Fragment}>
      <Dialog as="div" className="relative z-50" onClose={onClose}>
        <Transition.Child
          as={Fragment}
          enter="ease-out duration-300"
          enterFrom="opacity-0"
          enterTo="opacity-100"
          leave="ease-in duration-200"
          leaveFrom="opacity-100"
          leaveTo="opacity-0"
        >
          <div className="modal-backdrop" />
        </Transition.Child>

        <div className="fixed inset-0 overflow-y-auto">
          <div className="flex min-h-full items-center justify-center p-4">
            <Transition.Child
              as={Fragment}
              enter="ease-out duration-300"
              enterFrom="opacity-0 scale-95"
              enterTo="opacity-100 scale-100"
              leave="ease-in duration-200"
              leaveFrom="opacity-100 scale-100"
              leaveTo="opacity-0 scale-95"
            >
              <Dialog.Panel className="panel w-full max-w-2xl transform transition-all">
                <Dialog.Title
                  as="h3"
                  className="text-2xl font-bold glow-text text-pink-400 mb-6"
                >
                  Satellite Details
                  <span className="ml-3 seven-segment text-green-400">{catid}</span>
                </Dialog.Title>
                
                {loading && (
                  <div className="flex items-center justify-center py-12">
                    <div className="spinner"></div>
                    <span className="ml-3 text-cyan-300">Loading metadata...</span>
                  </div>
                )}
                
                {error && (
                  <div className="text-red-400 text-center py-8">
                    {error}
                  </div>
                )}
                
                {!loading && !error && metadata && (
                  <div className="space-y-4">
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <label className="block text-sm font-bold text-pink-300 mb-1">
                          Name
                        </label>
                        <p className="text-cyan-200 bg-black/30 p-2 rounded beveled">
                          {metadata.name || 'N/A'}
                        </p>
                      </div>
                      
                      <div>
                        <label className="block text-sm font-bold text-pink-300 mb-1">
                          Status
                        </label>
                        <p className="text-cyan-200 bg-black/30 p-2 rounded beveled">
                          {metadata.status || 'Unknown'}
                        </p>
                      </div>
                    </div>
                    
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <label className="block text-sm font-bold text-pink-300 mb-1">
                          Operator
                        </label>
                        <p className="text-cyan-200 bg-black/30 p-2 rounded beveled">
                          {metadata.operator || 'N/A'}
                        </p>
                      </div>
                      
                      <div>
                        <label className="block text-sm font-bold text-pink-300 mb-1">
                          Country
                        </label>
                        <p className="text-cyan-200 bg-black/30 p-2 rounded beveled">
                          {metadata.country || 'N/A'}
                        </p>
                      </div>
                    </div>
                    
                    {metadata.mission && (
                      <div>
                        <label className="block text-sm font-bold text-pink-300 mb-1">
                          Mission / Description
                        </label>
                        <p className="text-cyan-200 bg-black/30 p-2 rounded beveled">
                          {metadata.mission}
                        </p>
                      </div>
                    )}
                    
                    {metadata.aliases && metadata.aliases.length > 0 && (
                      <div>
                        <label className="block text-sm font-bold text-pink-300 mb-1">
                          Aliases
                        </label>
                        <p className="text-cyan-200 bg-black/30 p-2 rounded beveled">
                          {metadata.aliases.join(', ')}
                        </p>
                      </div>
                    )}
                    
                    {metadata.orbit && (
                      <div>
                        <label className="block text-sm font-bold text-pink-300 mb-1">
                          Orbit
                        </label>
                        <div className="bg-black/30 p-3 rounded beveled space-y-1">
                          {metadata.orbit.type && (
                            <p className="text-cyan-200">
                              <span className="text-pink-300 font-bold">Type:</span> {metadata.orbit.type}
                            </p>
                          )}
                          {metadata.orbit.period !== undefined && (
                            <p className="text-cyan-200">
                              <span className="text-pink-300 font-bold">Period:</span> {metadata.orbit.period.toFixed(2)} min
                            </p>
                          )}
                          {metadata.orbit.inclination !== undefined && (
                            <p className="text-cyan-200">
                              <span className="text-pink-300 font-bold">Inclination:</span> {metadata.orbit.inclination.toFixed(2)}°
                            </p>
                          )}
                        </div>
                      </div>
                    )}
                    
                    <div>
                      <label className="block text-sm font-bold text-pink-300 mb-1">
                        Data Sources
                      </label>
                      <p className="text-cyan-200 bg-black/30 p-2 rounded beveled text-sm">
                        {metadata.sources.length > 0 ? metadata.sources.join(', ') : 'None'}
                      </p>
                    </div>
                  </div>
                )}
                
                <div className="mt-6 flex justify-end">
                  <button
                    onClick={onClose}
                    className="btn-retro"
                  >
                    CLOSE
                  </button>
                </div>
              </Dialog.Panel>
            </Transition.Child>
          </div>
        </div>
      </Dialog>
    </Transition>
  );
}
