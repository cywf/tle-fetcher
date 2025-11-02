import { useEffect, useState } from 'react';
import {
  Chart as ChartJS,
  ArcElement,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
} from 'chart.js';
import { Pie, Line } from 'react-chartjs-2';

ChartJS.register(
  ArcElement,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend
);

interface RepoStats {
  stars: number;
  forks: number;
  watchers: number;
  languages: { [key: string]: number };
  commitActivity: Array<{ week: string; commits: number }>;
  openIssues: number;
  lastUpdated: string;
}

export default function StatisticsCharts() {
  const [stats, setStats] = useState<RepoStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const basePath = import.meta.env.BASE_URL || '';
    fetch(`${basePath}/data/stats.json`)
      .then((res) => {
        if (!res.ok) throw new Error('Failed to load statistics');
        return res.json();
      })
      .then((data) => {
        setStats(data);
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message);
        setLoading(false);
      });
  }, []);

  if (loading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {[...Array(4)].map((_, i) => (
          <div key={i} className="card bg-base-200 shadow-lg">
            <div className="card-body">
              <div className="skeleton h-8 w-48 mb-4"></div>
              <div className="skeleton h-64 w-full"></div>
            </div>
          </div>
        ))}
      </div>
    );
  }

  if (error || !stats) {
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
          <h3 className="font-bold">Statistics Not Available</h3>
          <div className="text-sm">
            {error || 'Statistics data has not been generated yet. This will be populated by CI.'}
          </div>
        </div>
      </div>
    );
  }

  // Prepare language chart data
  const languageData = {
    labels: Object.keys(stats.languages),
    datasets: [
      {
        data: Object.values(stats.languages),
        backgroundColor: [
          'rgba(124, 58, 237, 0.8)',
          'rgba(45, 212, 191, 0.8)',
          'rgba(245, 158, 11, 0.8)',
          'rgba(239, 68, 68, 0.8)',
          'rgba(59, 130, 246, 0.8)',
          'rgba(16, 185, 129, 0.8)',
        ],
        borderColor: [
          'rgba(124, 58, 237, 1)',
          'rgba(45, 212, 191, 1)',
          'rgba(245, 158, 11, 1)',
          'rgba(239, 68, 68, 1)',
          'rgba(59, 130, 246, 1)',
          'rgba(16, 185, 129, 1)',
        ],
        borderWidth: 2,
      },
    ],
  };

  // Prepare commit activity chart data
  const commitData = {
    labels: stats.commitActivity.map((w) => w.week),
    datasets: [
      {
        label: 'Commits',
        data: stats.commitActivity.map((w) => w.commits),
        borderColor: 'rgba(124, 58, 237, 1)',
        backgroundColor: 'rgba(124, 58, 237, 0.2)',
        tension: 0.4,
      },
    ],
  };

  const chartOptions = {
    responsive: true,
    maintainAspectRatio: true,
    plugins: {
      legend: {
        labels: {
          color: 'rgba(255, 255, 255, 0.87)',
        },
      },
    },
    scales: {
      x: {
        ticks: { color: 'rgba(255, 255, 255, 0.7)' },
        grid: { color: 'rgba(255, 255, 255, 0.1)' },
      },
      y: {
        ticks: { color: 'rgba(255, 255, 255, 0.7)' },
        grid: { color: 'rgba(255, 255, 255, 0.1)' },
      },
    },
  };

  return (
    <div className="space-y-6">
      {/* Stats Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="stat bg-base-200 rounded-lg shadow-lg">
          <div className="stat-figure text-primary">
            <svg className="w-8 h-8" fill="currentColor" viewBox="0 0 20 20">
              <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
            </svg>
          </div>
          <div className="stat-title">Stars</div>
          <div className="stat-value text-primary">{stats.stars}</div>
        </div>

        <div className="stat bg-base-200 rounded-lg shadow-lg">
          <div className="stat-figure text-secondary">
            <svg className="w-8 h-8" fill="currentColor" viewBox="0 0 20 20">
              <path d="M7 9a2 2 0 012-2h6a2 2 0 012 2v6a2 2 0 01-2 2H9a2 2 0 01-2-2V9z" />
              <path d="M5 3a2 2 0 00-2 2v6a2 2 0 002 2V5h8a2 2 0 00-2-2H5z" />
            </svg>
          </div>
          <div className="stat-title">Forks</div>
          <div className="stat-value text-secondary">{stats.forks}</div>
        </div>

        <div className="stat bg-base-200 rounded-lg shadow-lg">
          <div className="stat-figure text-accent">
            <svg className="w-8 h-8" fill="currentColor" viewBox="0 0 20 20">
              <path d="M10 12a2 2 0 100-4 2 2 0 000 4z" />
              <path fillRule="evenodd" d="M.458 10C1.732 5.943 5.522 3 10 3s8.268 2.943 9.542 7c-1.274 4.057-5.064 7-9.542 7S1.732 14.057.458 10zM14 10a4 4 0 11-8 0 4 4 0 018 0z" clipRule="evenodd" />
            </svg>
          </div>
          <div className="stat-title">Watchers</div>
          <div className="stat-value text-accent">{stats.watchers}</div>
        </div>

        <div className="stat bg-base-200 rounded-lg shadow-lg">
          <div className="stat-figure text-info">
            <svg className="w-8 h-8" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
            </svg>
          </div>
          <div className="stat-title">Open Issues</div>
          <div className="stat-value text-info">{stats.openIssues}</div>
        </div>
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="card bg-base-200 shadow-lg">
          <div className="card-body">
            <h2 className="card-title">Language Breakdown</h2>
            <div className="h-64 flex items-center justify-center">
              <Pie data={languageData} options={{ responsive: true, maintainAspectRatio: true }} />
            </div>
          </div>
        </div>

        <div className="card bg-base-200 shadow-lg">
          <div className="card-body">
            <h2 className="card-title">12-Week Commit Activity</h2>
            <div className="h-64">
              <Line data={commitData} options={chartOptions} />
            </div>
          </div>
        </div>
      </div>

      {/* Last Updated */}
      <div className="text-center text-sm opacity-70">
        Last updated: {new Date(stats.lastUpdated).toLocaleString()}
      </div>
    </div>
  );
}
