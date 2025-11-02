import * as fs from 'fs';
import * as path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

interface TLEEntry {
  id: string;
  name?: string;
  epoch?: string;
  path: string;
}

function scanTLEFiles(dir: string, baseDir: string): TLEEntry[] {
  const entries: TLEEntry[] = [];
  
  if (!fs.existsSync(dir)) {
    console.log(`TLE directory not found: ${dir}`);
    return entries;
  }

  const files = fs.readdirSync(dir, { withFileTypes: true });
  
  for (const file of files) {
    const fullPath = path.join(dir, file.name);
    
    if (file.isDirectory()) {
      entries.push(...scanTLEFiles(fullPath, baseDir));
    } else if (file.name.endsWith('.tle')) {
      try {
        const content = fs.readFileSync(fullPath, 'utf-8');
        const lines = content.split('\n').filter(line => line.trim());
        
        // Extract NORAD ID from filename or TLE content
        const idMatch = file.name.match(/(\d+)\.tle/);
        const id = idMatch ? idMatch[1] : 'unknown';
        
        // Try to extract name from first line if it exists
        let name: string | undefined;
        if (lines.length > 0 && !lines[0].startsWith('1 ')) {
          name = lines[0].trim();
        }
        
        // Try to extract epoch from line 1
        let epoch: string | undefined;
        const line1 = lines.find(l => l.startsWith('1 '));
        if (line1) {
          // Epoch is in columns 19-32 of line 1
          const epochStr = line1.substring(18, 32).trim();
          // Convert TLE epoch format (YYDDD.FFFFFFFF) to approximate date
          if (epochStr) {
            try {
              const year = parseInt(epochStr.substring(0, 2));
              const fullYear = year < 57 ? 2000 + year : 1900 + year;
              const dayOfYear = parseFloat(epochStr.substring(2));
              const epochDate = new Date(fullYear, 0, 1);
              epochDate.setDate(dayOfYear);
              epoch = epochDate.toISOString();
            } catch (e) {
              // Ignore epoch parsing errors
            }
          }
        }
        
        const relativePath = '/' + path.relative(baseDir, fullPath).replace(/\\/g, '/');
        
        entries.push({
          id,
          name,
          epoch,
          path: relativePath,
        });
      } catch (error) {
        console.error(`Error reading TLE file ${fullPath}:`, error);
      }
    }
  }
  
  return entries;
}

function main() {
  const publicDir = path.join(__dirname, '..', 'public');
  const tleDir = path.join(publicDir, 'tle');
  const outputPath = path.join(tleDir, 'catalog.json');
  
  console.log('Scanning TLE files in:', tleDir);
  
  const catalog = scanTLEFiles(tleDir, publicDir);
  
  console.log(`Found ${catalog.length} TLE files`);
  
  // Ensure directory exists
  fs.mkdirSync(path.dirname(outputPath), { recursive: true });
  
  // Write catalog
  fs.writeFileSync(outputPath, JSON.stringify(catalog, null, 2), 'utf-8');
  
  console.log('TLE catalog written to:', outputPath);
}

main();
