import { useEffect, useState, useRef } from 'react';
import mermaid from 'mermaid';

interface Diagram {
  id: string;
  name: string;
  path: string;
}

export default function MermaidViewer() {
  const [diagrams, setDiagrams] = useState<Diagram[]>([]);
  const [selectedDiagram, setSelectedDiagram] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const mermaidRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    mermaid.initialize({
      startOnLoad: false,
      theme: 'dark',
      themeVariables: {
        darkMode: true,
        background: '#0f172a',
        primaryColor: '#7c3aed',
        secondaryColor: '#2dd4bf',
        tertiaryColor: '#f59e0b',
      },
    });

    // Try to load diagram list
    const basePath = import.meta.env.BASE_URL || '';
    fetch(`${basePath}/diagrams/diagrams.json`)
      .then((res) => {
        if (!res.ok) throw new Error('No diagrams found');
        return res.json();
      })
      .then((data: Diagram[]) => {
        setDiagrams(data);
        setLoading(false);
        
        // Select first diagram or from hash
        const hash = window.location.hash.slice(1);
        const initial = hash || (data.length > 0 ? data[0].id : null);
        if (initial) {
          loadDiagram(initial);
        }
      })
      .catch((err) => {
        setError(err.message);
        setLoading(false);
      });
  }, []);

  const loadDiagram = async (diagramId: string) => {
    setSelectedDiagram(diagramId);
    window.location.hash = diagramId;
    
    const diagram = diagrams.find((d) => d.id === diagramId);
    if (!diagram) return;

    try {
      const basePath = import.meta.env.BASE_URL || '';
      const response = await fetch(`${basePath}${diagram.path}`);
      if (!response.ok) throw new Error('Failed to load diagram');
      
      const content = await response.text();
      
      // Render mermaid diagram
      if (mermaidRef.current) {
        mermaidRef.current.innerHTML = '';
        const { svg } = await mermaid.render(`mermaid-${diagramId}`, content);
        mermaidRef.current.innerHTML = svg;
      }
    } catch (err: any) {
      console.error('Error loading diagram:', err);
      setError(err.message);
    }
  };

  useEffect(() => {
    if (selectedDiagram && diagrams.length > 0) {
      loadDiagram(selectedDiagram);
    }
  }, [selectedDiagram, diagrams]);

  if (loading) {
    return (
      <div className="text-center py-20">
        <div className="loading loading-spinner loading-lg"></div>
        <p className="mt-4">Loading diagrams...</p>
      </div>
    );
  }

  if (error || diagrams.length === 0) {
    return (
      <div className="space-y-6">
        <div className="alert alert-warning shadow-lg">
          <svg
            xmlns="http://www.w3.org/2000/svg"
            className="stroke-current shrink-0 h-6 w-6"
            fill="none"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth="2"
              d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
            />
          </svg>
          <div>
            <h3 className="font-bold">No Diagrams Found</h3>
            <div className="text-sm">
              {error || 'No Mermaid diagrams have been created yet.'}
            </div>
          </div>
        </div>

        <div className="card bg-base-200 shadow-lg">
          <div className="card-body">
            <h2 className="card-title">How to Add Diagrams</h2>
            <ol className="list-decimal list-inside space-y-2 opacity-80">
              <li>Create <code>.mmd</code> files in the <code>/mermaid/</code> directory of the repository</li>
              <li>Write your Mermaid diagram syntax in the file</li>
              <li>The build process will automatically copy them to <code>site/public/diagrams/</code></li>
              <li>They will appear here once the site is rebuilt and deployed</li>
            </ol>
            
            <div className="divider"></div>
            
            <h3 className="font-bold text-lg mb-2">Example Mermaid Diagram</h3>
            <div className="mockup-code text-sm">
              <pre><code>{`graph TD
    A[Start] --> B{Decision}
    B -->|Yes| C[Action 1]
    B -->|No| D[Action 2]
    C --> E[End]
    D --> E`}</code></pre>
            </div>
            
            <div className="card-actions justify-end mt-4">
              <a
                href="https://mermaid.js.org/intro/"
                target="_blank"
                rel="noopener noreferrer"
                className="btn btn-primary"
              >
                Learn Mermaid Syntax
              </a>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
      {/* Diagram List */}
      <div className="lg:col-span-1">
        <div className="card bg-base-200 shadow-lg sticky top-24">
          <div className="card-body">
            <h2 className="card-title mb-4">Diagrams</h2>
            <ul className="menu menu-compact">
              {diagrams.map((diagram) => (
                <li key={diagram.id}>
                  <button
                    onClick={() => loadDiagram(diagram.id)}
                    className={selectedDiagram === diagram.id ? 'active' : ''}
                  >
                    {diagram.name}
                  </button>
                </li>
              ))}
            </ul>
          </div>
        </div>
      </div>

      {/* Diagram Viewer */}
      <div className="lg:col-span-3">
        <div className="card bg-base-200 shadow-lg">
          <div className="card-body">
            {selectedDiagram && (
              <>
                <h2 className="card-title mb-4">
                  {diagrams.find((d) => d.id === selectedDiagram)?.name}
                </h2>
                <div
                  ref={mermaidRef}
                  className="flex justify-center items-center p-6 bg-base-300 rounded-lg overflow-auto"
                  style={{ minHeight: '400px' }}
                />
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
