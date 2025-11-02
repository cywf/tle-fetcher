import * as fs from 'fs';
import * as path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const GITHUB_TOKEN = process.env.GITHUB_TOKEN;
const REPO_OWNER = 'cywf';
const REPO_NAME = 'tle-fetcher';

interface ProjectItem {
  id: string;
  title: string;
  status: string;
  url: string;
  labels: string[];
  assignees: string[];
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

function determineStatus(labels: string[]): string {
  const statusLabels = labels.map(l => l.toLowerCase());
  
  if (statusLabels.some(l => l.includes('done') || l.includes('completed'))) {
    return 'done';
  }
  if (statusLabels.some(l => l.includes('doing') || l.includes('in progress') || l.includes('wip'))) {
    return 'doing';
  }
  return 'todo';
}

async function main() {
  try {
    console.log('Fetching project data...');
    
    // Try to fetch issues grouped by labels
    // This is a fallback approach when Projects v2 API is not accessible
    const issues = await fetchWithAuth(
      `https://api.github.com/repos/${REPO_OWNER}/${REPO_NAME}/issues?state=open&per_page=100`
    );
    
    const projectItems: ProjectItem[] = issues.map((issue: any) => {
      const labels = issue.labels?.map((l: any) => l.name) || [];
      const assignees = issue.assignees?.map((a: any) => a.login) || [];
      
      return {
        id: issue.id.toString(),
        title: issue.title,
        status: determineStatus(labels),
        url: issue.html_url,
        labels,
        assignees,
      };
    });
    
    // Write to file
    const outputDir = path.join(__dirname, '..', '..', 'public', 'data');
    fs.mkdirSync(outputDir, { recursive: true });
    
    const outputPath = path.join(outputDir, 'projects.json');
    fs.writeFileSync(outputPath, JSON.stringify(projectItems, null, 2), 'utf-8');
    
    console.log(`${projectItems.length} project items written to:`, outputPath);
    
    // Log status breakdown
    const statusCounts = {
      todo: projectItems.filter(i => i.status === 'todo').length,
      doing: projectItems.filter(i => i.status === 'doing').length,
      done: projectItems.filter(i => i.status === 'done').length,
    };
    console.log('Status breakdown:', statusCounts);
  } catch (error) {
    console.error('Error fetching project data:', error);
    // Don't fail the build
    console.log('Writing empty projects array...');
    const outputDir = path.join(__dirname, '..', '..', 'public', 'data');
    fs.mkdirSync(outputDir, { recursive: true });
    fs.writeFileSync(
      path.join(outputDir, 'projects.json'),
      JSON.stringify([], null, 2),
      'utf-8'
    );
  }
}

main();
