import { useEffect, useState } from 'react';

interface Discussion {
  number: number;
  title: string;
  url: string;
  author: string;
  category: string;
  comments: number;
  createdAt: string;
  updatedAt: string;
}

export default function DiscussionsList() {
  const [discussions, setDiscussions] = useState<Discussion[]>([]);
  const [filteredDiscussions, setFilteredDiscussions] = useState<Discussion[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [categoryFilter, setCategoryFilter] = useState('all');

  useEffect(() => {
    const basePath = import.meta.env.BASE_URL || '';
    fetch(`${basePath}/data/discussions.json`)
      .then((res) => {
        if (!res.ok) throw new Error('Failed to load discussions');
        return res.json();
      })
      .then((data) => {
        setDiscussions(data);
        setFilteredDiscussions(data);
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message);
        setLoading(false);
      });
  }, []);

  useEffect(() => {
    let filtered = discussions;

    if (searchQuery) {
      filtered = filtered.filter(
        (d) =>
          d.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
          d.author.toLowerCase().includes(searchQuery.toLowerCase())
      );
    }

    if (categoryFilter !== 'all') {
      filtered = filtered.filter((d) => d.category === categoryFilter);
    }

    setFilteredDiscussions(filtered);
  }, [searchQuery, categoryFilter, discussions]);

  if (loading) {
    return (
      <div className="space-y-4">
        {[...Array(5)].map((_, i) => (
          <div key={i} className="card bg-base-200 shadow-lg">
            <div className="card-body">
              <div className="skeleton h-6 w-3/4 mb-2"></div>
              <div className="skeleton h-4 w-full"></div>
              <div className="skeleton h-4 w-2/3"></div>
            </div>
          </div>
        ))}
      </div>
    );
  }

  if (error || discussions.length === 0) {
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
          <h3 className="font-bold">Discussions Not Available</h3>
          <div className="text-sm">
            {error || 'Discussions data has not been generated yet. This will be populated by CI.'}
          </div>
        </div>
      </div>
    );
  }

  const categories = Array.from(new Set(discussions.map((d) => d.category)));

  return (
    <div className="space-y-6">
      {/* Search and Filter */}
      <div className="flex flex-col sm:flex-row gap-4">
        <div className="form-control flex-1">
          <input
            type="text"
            placeholder="Search discussions..."
            className="input input-bordered w-full"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
        </div>
        <div className="form-control">
          <select
            className="select select-bordered"
            value={categoryFilter}
            onChange={(e) => setCategoryFilter(e.target.value)}
          >
            <option value="all">All Categories</option>
            {categories.map((cat) => (
              <option key={cat} value={cat}>
                {cat}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Results Count */}
      <div className="text-sm opacity-70">
        Showing {filteredDiscussions.length} of {discussions.length} discussions
      </div>

      {/* Discussions List */}
      <div className="space-y-4">
        {filteredDiscussions.map((discussion) => (
          <a
            key={discussion.number}
            href={discussion.url}
            target="_blank"
            rel="noopener noreferrer"
            className="card bg-base-200 hover:bg-base-300 transition-colors shadow-lg"
          >
            <div className="card-body">
              <div className="flex justify-between items-start gap-4">
                <div className="flex-1">
                  <h3 className="card-title text-lg mb-2">{discussion.title}</h3>
                  <div className="flex flex-wrap gap-2 text-sm">
                    <span className="badge badge-primary">{discussion.category}</span>
                    <span className="opacity-70">by {discussion.author}</span>
                    <span className="opacity-70">•</span>
                    <span className="opacity-70">{discussion.comments} comments</span>
                  </div>
                </div>
                <div className="text-xs opacity-70 whitespace-nowrap">
                  {new Date(discussion.updatedAt).toLocaleDateString()}
                </div>
              </div>
            </div>
          </a>
        ))}
      </div>

      {filteredDiscussions.length === 0 && (
        <div className="text-center py-12 opacity-70">
          <p>No discussions found matching your criteria.</p>
        </div>
      )}
    </div>
  );
}
