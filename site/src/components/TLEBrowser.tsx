import { useEffect, useState } from 'react';

interface TLEEntry {
  id: string;
  name?: string;
  epoch?: string;
  path: string;
}

export default function TLEBrowser() {
  const [catalog, setCatalog] = useState<TLEEntry[]>([]);
  const [filteredCatalog, setFilteredCatalog] = useState<TLEEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');

  useEffect(() => {
    const basePath = import.meta.env.BASE_URL || '';
    fetch(`${basePath}/tle/catalog.json`)
      .then((res) => {
        if (!res.ok) throw new Error('Failed to load TLE catalog');
        return res.json();
      })
      .then((data: TLEEntry[]) => {
        setCatalog(data);
        setFilteredCatalog(data);
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message);
        setLoading(false);
      });
  }, []);

  useEffect(() => {
    if (searchQuery) {
      const filtered = catalog.filter(
        (entry) =>
          entry.id.toLowerCase().includes(searchQuery.toLowerCase()) ||
          entry.name?.toLowerCase().includes(searchQuery.toLowerCase())
      );
      setFilteredCatalog(filtered);
    } else {
      setFilteredCatalog(catalog);
    }
  }, [searchQuery, catalog]);

  if (loading) {
    return (
      <div className="space-y-4">
        {[...Array(10)].map((_, i) => (
          <div key={i} className="skeleton h-16 w-full"></div>
        ))}
      </div>
    );
  }

  if (error || catalog.length === 0) {
    return (
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
          <h3 className="font-bold">TLE Catalog Not Available</h3>
          <div className="text-sm">
            {error || 'TLE catalog has not been generated yet. This will be populated by CI.'}
          </div>
        </div>
      </div>
    );
  }

  const basePath = import.meta.env.BASE_URL || '';

  return (
    <div className="space-y-6">
      {/* Search */}
      <div className="form-control">
        <input
          type="text"
          placeholder="Search by ID or name..."
          className="input input-bordered w-full"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
        />
      </div>

      {/* Results Count */}
      <div className="text-sm opacity-70">
        Showing {filteredCatalog.length} of {catalog.length} TLE files
      </div>

      {/* TLE List */}
      <div className="overflow-x-auto">
        <table className="table table-zebra">
          <thead>
            <tr>
              <th>NORAD ID</th>
              <th>Name</th>
              <th>Epoch</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {filteredCatalog.map((entry) => (
              <tr key={entry.id}>
                <td className="font-mono">{entry.id}</td>
                <td>{entry.name || 'N/A'}</td>
                <td className="text-sm opacity-70">
                  {entry.epoch ? new Date(entry.epoch).toLocaleDateString() : 'N/A'}
                </td>
                <td>
                  <a
                    href={`${basePath}${entry.path}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="btn btn-sm btn-ghost"
                  >
                    View TLE →
                  </a>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {filteredCatalog.length === 0 && (
        <div className="text-center py-12 opacity-70">
          <p>No TLE files found matching your search.</p>
        </div>
      )}
    </div>
  );
}
