import * as fs from 'fs';
import * as path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const GITHUB_TOKEN = process.env.GITHUB_TOKEN;
const REPO_OWNER = 'cywf';
const REPO_NAME = 'tle-fetcher';

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

async function fetchWithAuth(query: string) {
  const headers: HeadersInit = {
    'Accept': 'application/vnd.github.v3+json',
    'Content-Type': 'application/json',
    'User-Agent': 'TLE-Fetcher-Site',
  };
  
  if (GITHUB_TOKEN) {
    headers['Authorization'] = `Bearer ${GITHUB_TOKEN}`;
  }
  
  const response = await fetch('https://api.github.com/graphql', {
    method: 'POST',
    headers,
    body: JSON.stringify({ query }),
  });
  
  if (!response.ok) {
    throw new Error(`GitHub API error: ${response.status} ${response.statusText}`);
  }
  
  return response.json();
}

async function main() {
  try {
    console.log('Fetching discussions...');
    
    const query = `
      query {
        repository(owner: "${REPO_OWNER}", name: "${REPO_NAME}") {
          discussions(first: 25, orderBy: {field: UPDATED_AT, direction: DESC}) {
            nodes {
              number
              title
              url
              author {
                login
              }
              category {
                name
              }
              comments {
                totalCount
              }
              createdAt
              updatedAt
            }
          }
        }
      }
    `;
    
    const result = await fetchWithAuth(query);
    
    const discussions: Discussion[] = result.data?.repository?.discussions?.nodes?.map((node: any) => ({
      number: node.number,
      title: node.title,
      url: node.url,
      author: node.author?.login || 'Unknown',
      category: node.category?.name || 'General',
      comments: node.comments?.totalCount || 0,
      createdAt: node.createdAt,
      updatedAt: node.updatedAt,
    })) || [];
    
    // Write to file
    const outputDir = path.join(__dirname, '..', '..', 'public', 'data');
    fs.mkdirSync(outputDir, { recursive: true });
    
    const outputPath = path.join(outputDir, 'discussions.json');
    fs.writeFileSync(outputPath, JSON.stringify(discussions, null, 2), 'utf-8');
    
    console.log(`${discussions.length} discussions written to:`, outputPath);
  } catch (error) {
    console.error('Error fetching discussions:', error);
    // Don't fail the build if discussions can't be fetched
    console.log('Writing empty discussions array...');
    const outputDir = path.join(__dirname, '..', '..', 'public', 'data');
    fs.mkdirSync(outputDir, { recursive: true });
    fs.writeFileSync(
      path.join(outputDir, 'discussions.json'),
      JSON.stringify([], null, 2),
      'utf-8'
    );
  }
}

main();
