interface GaugesProps {
  passCount: number;
  maxPassCount?: number;
}

export default function Gauges({ passCount, maxPassCount = 50 }: GaugesProps) {
  const percentage = Math.min(100, (passCount / maxPassCount) * 100);
  
  return (
    <div className="panel">
      <h3 className="text-xl font-bold glow-text text-pink-400 mb-4">
        System Status
      </h3>
      
      <div className="flex items-center gap-6">
        {/* LED indicators */}
        <div className="flex flex-col gap-3">
          <div className="flex items-center gap-2">
            <div className="led bg-green-400 led-active"></div>
            <span className="text-cyan-300 text-sm">SYSTEM READY</span>
          </div>
          <div className="flex items-center gap-2">
            <div className={`led ${passCount > 0 ? 'bg-blue-400 led-active' : 'bg-gray-600'}`}></div>
            <span className="text-cyan-300 text-sm">TRACKING ACTIVE</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="led bg-yellow-400"></div>
            <span className="text-cyan-300 text-sm">DATA LINK OK</span>
          </div>
        </div>
        
        {/* Analog gauge */}
        <div className="flex-1">
          <div className="relative">
            <label className="block text-sm font-bold text-pink-300 mb-2">
              DETECTED SATELLITES
            </label>
            <div className="h-8 bg-black/50 border-2 border-cyan-500/50 rounded beveled overflow-hidden">
              <div
                className="h-full bg-gradient-to-r from-green-500 via-yellow-500 to-red-500 transition-all duration-500"
                style={{ width: `${percentage}%` }}
              ></div>
            </div>
            <div className="flex justify-between mt-1 text-xs text-cyan-300">
              <span>0</span>
              <span className="seven-segment text-green-400 text-lg">{passCount}</span>
              <span>{maxPassCount}</span>
            </div>
          </div>
        </div>
      </div>
      
      {/* Additional metrics */}
      <div className="mt-6 grid grid-cols-3 gap-4">
        <div className="bg-black/30 p-3 rounded beveled">
          <p className="text-xs text-pink-300 uppercase font-bold">Signal Quality</p>
          <p className="seven-segment text-green-400 text-xl">98.7%</p>
        </div>
        <div className="bg-black/30 p-3 rounded beveled">
          <p className="text-xs text-pink-300 uppercase font-bold">Compute Time</p>
          <p className="seven-segment text-green-400 text-xl">&lt;1s</p>
        </div>
        <div className="bg-black/30 p-3 rounded beveled">
          <p className="text-xs text-pink-300 uppercase font-bold">Network</p>
          <p className="seven-segment text-green-400 text-xl">OK</p>
        </div>
      </div>
    </div>
  );
}
