import { useEffect, useState } from 'react';

interface ProjectItem {
  id: string;
  title: string;
  status: string;
  url: string;
  labels: string[];
  assignees: string[];
}

export default function DevelopmentBoard() {
  const [items, setItems] = useState<ProjectItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const basePath = import.meta.env.BASE_URL || '';
    fetch(`${basePath}/data/projects.json`)
      .then((res) => {
        if (!res.ok) throw new Error('Failed to load project data');
        return res.json();
      })
      .then((data) => {
        setItems(data);
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message);
        setLoading(false);
      });
  }, []);

  if (loading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {['To Do', 'In Progress', 'Done'].map((status) => (
          <div key={status} className="card bg-base-200 shadow-lg">
            <div className="card-body">
              <div className="skeleton h-8 w-32 mb-4"></div>
              {[...Array(3)].map((_, i) => (
                <div key={i} className="skeleton h-24 w-full mb-2"></div>
              ))}
            </div>
          </div>
        ))}
      </div>
    );
  }

  if (error || items.length === 0) {
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
          <h3 className="font-bold">Project Board Not Available</h3>
          <div className="text-sm">
            {error || 'Project data has not been generated yet. This will be populated by CI.'}
          </div>
        </div>
      </div>
    );
  }

  // Group items by status
  const columns = [
    { title: 'To Do', status: 'todo', color: 'badge-error' },
    { title: 'In Progress', status: 'doing', color: 'badge-warning' },
    { title: 'Done', status: 'done', color: 'badge-success' },
  ];

  const getItemsByStatus = (status: string) =>
    items.filter((item) => item.status.toLowerCase() === status);

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
      {columns.map((column) => {
        const columnItems = getItemsByStatus(column.status);
        return (
          <div key={column.status} className="space-y-4">
            <div className="card bg-base-200 shadow-lg">
              <div className="card-body p-4">
                <div className="flex justify-between items-center">
                  <h2 className="card-title text-xl">{column.title}</h2>
                  <span className={`badge ${column.color}`}>
                    {columnItems.length}
                  </span>
                </div>
              </div>
            </div>

            <div className="space-y-3">
              {columnItems.map((item) => (
                <a
                  key={item.id}
                  href={item.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="card bg-base-300 hover:bg-base-100 transition-colors shadow-md"
                >
                  <div className="card-body p-4">
                    <h3 className="font-semibold text-sm mb-2">{item.title}</h3>
                    
                    {item.labels.length > 0 && (
                      <div className="flex flex-wrap gap-1 mb-2">
                        {item.labels.map((label) => (
                          <span key={label} className="badge badge-sm badge-outline">
                            {label}
                          </span>
                        ))}
                      </div>
                    )}
                    
                    {item.assignees.length > 0 && (
                      <div className="flex items-center gap-2 text-xs opacity-70">
                        <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                          <path
                            fillRule="evenodd"
                            d="M10 9a3 3 0 100-6 3 3 0 000 6zm-7 9a7 7 0 1114 0H3z"
                            clipRule="evenodd"
                          />
                        </svg>
                        <span>{item.assignees.join(', ')}</span>
                      </div>
                    )}
                  </div>
                </a>
              ))}

              {columnItems.length === 0 && (
                <div className="card bg-base-300 shadow-md opacity-50">
                  <div className="card-body p-4 text-center text-sm">
                    No items
                  </div>
                </div>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}
