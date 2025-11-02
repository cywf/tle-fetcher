import * as fs from 'fs';
import * as path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const GITHUB_TOKEN = process.env.GITHUB_TOKEN;
const REPO_OWNER = 'cywf';
const REPO_NAME = 'tle-fetcher';

interface RepoStats {
  stars: number;
  forks: number;
  watchers: number;
  languages: { [key: string]: number };
  commitActivity: Array<{ week: string; commits: number }>;
  openIssues: number;
  lastUpdated: string;
}

async function fetchWithAuth(url: string) {
  const headers: HeadersInit = {
    'Accept': 'application/vnd.github.v3+json',
    'User-Agent': 'TLE-Fetcher-Site',
  };
  
  if (GITHUB_TOKEN) {
    headers['Authorization'] = `Bearer ${GITHUB_TOKEN}`;
  }
  
  const response = await fetch(url, { headers });
  
  if (!response.ok) {
    throw new Error(`GitHub API error: ${response.status} ${response.statusText}`);
  }
  
  return response.json();
}

async function main() {
  try {
    console.log('Fetching repository data...');
    
    // Fetch repository info
    const repo = await fetchWithAuth(`https://api.github.com/repos/${REPO_OWNER}/${REPO_NAME}`);
    
    // Fetch languages
    const languages = await fetchWithAuth(`https://api.github.com/repos/${REPO_OWNER}/${REPO_NAME}/languages`);
    
    // Fetch commit activity (last 12 weeks)
    const commitActivity = await fetchWithAuth(
      `https://api.github.com/repos/${REPO_OWNER}/${REPO_NAME}/stats/participation`
    );
    
    // Process commit activity into weekly data
    const weeklyCommits = commitActivity.all?.slice(-12) || [];
    const now = new Date();
    const commitData = weeklyCommits.map((commits: number, index: number) => {
      const weekDate = new Date(now);
      weekDate.setDate(weekDate.getDate() - (11 - index) * 7);
      return {
        week: weekDate.toISOString().split('T')[0],
        commits,
      };
    });
    
    const stats: RepoStats = {
      stars: repo.stargazers_count || 0,
      forks: repo.forks_count || 0,
      watchers: repo.subscribers_count || 0,
      languages,
      commitActivity: commitData,
      openIssues: repo.open_issues_count || 0,
      lastUpdated: new Date().toISOString(),
    };
    
    // Write to file
    const outputDir = path.join(__dirname, '..', '..', 'public', 'data');
    fs.mkdirSync(outputDir, { recursive: true });
    
    const outputPath = path.join(outputDir, 'stats.json');
    fs.writeFileSync(outputPath, JSON.stringify(stats, null, 2), 'utf-8');
    
    console.log('Repository statistics written to:', outputPath);
    console.log(`Stars: ${stats.stars}, Forks: ${stats.forks}, Watchers: ${stats.watchers}`);
  } catch (error) {
    console.error('Error fetching repository data:', error);
    process.exit(1);
  }
}

main();
