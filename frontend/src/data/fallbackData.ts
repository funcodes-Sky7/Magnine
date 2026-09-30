import targetsJson from './fallbackTargets.json';
import gridJson from './fallbackGrid.json';
import type { Target, Layer, ModelStatus, ModelVersion } from '../services/api';

/**
 * Single source of truth for priority classification.
 * Must match priority_from_prospectivity() in backend/app/geospatial/demo_data.py
 *   >= 0.80 → HIGH     (green)
 *   >= 0.60 → MODERATE (orange)
 *   <  0.60 → LOW      (grey)
 */
export function priorityFromProspectivity(score: number): 'HIGH' | 'MODERATE' | 'LOW' {
  if (score >= 0.80) return 'HIGH';
  if (score >= 0.60) return 'MODERATE';
  return 'LOW';
}

export const FALLBACK_TARGETS: Target[] = targetsJson as unknown as Target[];
export const FALLBACK_GRID = gridJson;

export const FALLBACK_LAYERS: Layer[] = [
  {
    id: 'sentinel2',
    name: 'Sentinel-2 True Color',
    description: 'Multispectral satellite imagery (10m resolution)',
    source: 'European Space Agency / Google Earth Engine',
    type: 'satellite',
    status: 'ready',
    default_visible: true,
    opacity: 0.85,
  },
  {
    id: 'geology',
    name: 'Geological Formations',
    description: 'Geological formations and lithological units',
    source: 'Geological Survey of India',
    type: 'vector',
    status: 'ready',
    default_visible: true,
    opacity: 0.6,
  },
  {
    id: 'occurrences',
    name: 'Mn Mines & Occurrences',
    description: 'Known manganese deposits, mines and prospects across India',
    source: 'IBM / GSI Published Data',
    type: 'point',
    status: 'ready',
    default_visible: true,
    opacity: 1.0,
  },
  {
    id: 'dem',
    name: 'Elevation (SRTM 30m)',
    description: 'Digital Elevation Model (SRTM 30m)',
    source: 'USGS SRTM / Earth Engine',
    type: 'raster',
    status: 'ready',
    default_visible: false,
    opacity: 0.5,
  },
  {
    id: 'faults',
    name: 'Faults & Shear Zones',
    description: 'Major fault systems and structural lineaments',
    source: 'GSI Structural Map',
    type: 'line',
    status: 'ready',
    default_visible: false,
    opacity: 0.9,
  },
  {
    id: 'prospectivity',
    name: 'AI Prospectivity Grid',
    description: 'Random Forest manganese prospectivity prediction grid (2,016 cells)',
    source: 'MANGANAI ML Model v2.0-gee',
    type: 'heatmap',
    status: 'ready',
    default_visible: false,
    opacity: 0.7,
  },
];

export const FALLBACK_OCCURRENCES = [
  { id: 'OCC001', name: 'Balaghat Mn Deposit', lat: 22.06, lng: 80.19, grade_pct: 42.3, state: 'Madhya Pradesh', status: 'Active Mine', type: 'Stratiform' },
  { id: 'OCC002', name: 'Dongri Buzurg', lat: 21.90, lng: 79.85, grade_pct: 38.7, state: 'Madhya Pradesh', status: 'Active Mine', type: 'Stratiform' },
  { id: 'OCC003', name: 'Sandur Mn Ore', lat: 15.07, lng: 76.56, grade_pct: 35.2, state: 'Karnataka', status: 'Active Mine', type: 'Supergene' },
  { id: 'OCC004', name: 'Vizianagaram Mn', lat: 18.12, lng: 83.41, grade_pct: 40.1, state: 'Andhra Pradesh', status: 'Active Mine', type: 'Stratiform' },
  { id: 'OCC005', name: 'Srikakulam Mn', lat: 18.29, lng: 83.90, grade_pct: 36.5, state: 'Andhra Pradesh', status: 'Active Mine', type: 'Stratiform' },
  { id: 'OCC006', name: 'Joda Mn Zone', lat: 21.78, lng: 85.33, grade_pct: 32.4, state: 'Odisha', status: 'Producing', type: 'BIF-hosted' },
  { id: 'OCC007', name: 'Bonai Mn Occurrence', lat: 21.90, lng: 84.85, grade_pct: 28.9, state: 'Odisha', status: 'Exploration', type: 'BIF-hosted' },
  { id: 'OCC008', name: 'Nagpur Mn Belt', lat: 21.15, lng: 79.07, grade_pct: 34.8, state: 'Maharashtra', status: 'Active Mine', type: 'Stratiform' },
  { id: 'OCC009', name: 'Tumsar Mn Zone', lat: 21.37, lng: 79.84, grade_pct: 31.2, state: 'Maharashtra', status: 'Exploration', type: 'Stratiform' },
  { id: 'OCC010', name: 'Panna Mn Prospect', lat: 24.72, lng: 80.18, grade_pct: 22.1, state: 'Madhya Pradesh', status: 'Prospect', type: 'Supergene' },
  { id: 'OCC011', name: 'Jaipur Mn Showings', lat: 20.15, lng: 82.55, grade_pct: 25.6, state: 'Odisha', status: 'Prospect', type: 'BIF-hosted' },
  { id: 'OCC012', name: 'Koraput Mn Zone', lat: 18.81, lng: 82.71, grade_pct: 29.3, state: 'Odisha', status: 'Exploration', type: 'Stratiform' },
  { id: 'OCC013', name: 'Chitradurga Mn Occurrence', lat: 14.22, lng: 76.40, grade_pct: 27.8, state: 'Karnataka', status: 'Prospect', type: 'Supergene' },
  { id: 'OCC014', name: 'Hospet Mn Zone', lat: 15.27, lng: 76.39, grade_pct: 30.1, state: 'Karnataka', status: 'Exploration', type: 'Supergene' },
  { id: 'OCC015', name: 'Sausar Valley Mn', lat: 21.65, lng: 79.20, grade_pct: 44.2, state: 'Maharashtra', status: 'Active Mine', type: 'Stratiform' },
];

export const FALLBACK_MODEL_STATUS: ModelStatus = {
  version: 'v2.0-gee',
  algorithm: 'Random Forest (300 trees) — GEE Sentinel-2 + SRTM',
  training_samples: 47,
  validated_samples: 12,
  f1_score: 0.68,
  recall: 0.70,
  precision: 0.66,
  accuracy: 0.618,
  is_active: true,
  created_at: '2026-09-30T00:00:00Z',
  feature_count: 14,
  features: [
    'slope', 'iron_oxide', 'B3 (Green)', 'B8 (NIR)', 'B2 (Blue)',
    'B12 (SWIR2)', 'B4 (Red)', 'aspect', 'elevation', 'fe_mn_index',
    'clay_ratio', 'NDVI', 'B11 (SWIR1)', 'b4_b8_ratio'
  ],
  feature_importance: {
    'slope': 0.1246,
    'iron_oxide': 0.1066,
    'B3 (Green)': 0.1065,
    'B8 (NIR)': 0.0834,
    'B2 (Blue)': 0.0787,
    'B12 (SWIR2)': 0.0743,
    'B4 (Red)': 0.0714,
    'aspect': 0.0700,
    'elevation': 0.0593,
    'fe_mn_index': 0.0489,
    'clay_ratio': 0.0478,
    'NDVI': 0.0462,
    'B11 (SWIR1)': 0.0455,
    'b4_b8_ratio': 0.0367,
  },
  status: 'Ready',
};

export const FALLBACK_MODEL_VERSIONS: ModelVersion[] = [
  {
    version: 'v2.0-gee',
    algorithm: 'Random Forest (300 trees) — GEE Sentinel-2 + SRTM',
    training_samples: 47,
    validated_samples: 12,
    f1_score: 0.68,
    recall: 0.70,
    precision: 0.66,
    accuracy: 0.618,
    is_active: true,
    created_at: '2026-09-30T00:00:00Z',
  },
  {
    version: 'v1.0-baseline',
    algorithm: 'Random Forest (100 trees) — Synthetic Demo',
    training_samples: 25,
    validated_samples: 5,
    f1_score: 0.58,
    recall: 0.60,
    precision: 0.56,
    accuracy: 0.55,
    is_active: false,
    created_at: '2026-09-28T00:00:00Z',
  }
];

export const FALLBACK_SUPPLY = {
  years: [2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025],
  domestic_production_mt: [2.8, 2.9, 2.4, 2.7, 3.1, 3.3, 3.5, 3.65],
  domestic_demand_mt: [4.1, 4.3, 3.9, 4.6, 5.0, 5.3, 5.6, 5.85],
  import_reliance_pct: [31.7, 32.5, 38.5, 41.3, 38.0, 37.7, 37.5, 37.6],
  imports_mt: [1.3, 1.4, 1.5, 1.9, 1.9, 2.0, 2.1, 2.2],
  top_import_sources: [
    { country: 'South Africa', share_pct: 68.4 },
    { country: 'Gabon', share_pct: 14.2 },
    { country: 'Australia', share_pct: 11.1 },
    { country: 'Other', share_pct: 6.3 },
  ],
  battery_demand_projected_mt_2030: 1.8,
  steel_demand_projected_mt_2030: 5.6,
  total_projected_demand_2030: 7.4,
  disclaimer: 'Scenario estimates for decision support. Not certified production forecasts.',
};

export const FALLBACK_SUPPLY_SCENARIOS = {
  years: [2026, 2027, 2028, 2029, 2030],
  scenarios: {
    current_trajectory: {
      name: 'Current trajectory',
      supply: [3.71, 3.78, 3.84, 3.90, 3.95],
      demand: [5.98, 6.32, 6.68, 7.05, 7.45],
      shortfall: [2.27, 2.54, 2.84, 3.15, 3.50],
      gap_2030: 3.50,
    },
    top1_target: {
      name: 'Add top 1 target',
      supply: [3.71, 3.82, 3.95, 4.08, 4.20],
      demand: [5.98, 6.32, 6.68, 7.05, 7.45],
      shortfall: [2.27, 2.50, 2.73, 2.97, 3.25],
      gap_2030: 3.25,
    },
    top5_targets: {
      name: 'Add top 5 targets',
      supply: [3.71, 3.95, 4.25, 4.58, 4.90],
      demand: [5.98, 6.32, 6.68, 7.05, 7.45],
      shortfall: [2.27, 2.37, 2.43, 2.47, 2.55],
      gap_2030: 2.55,
    },
    exploration_acceleration: {
      name: 'Exploration acceleration (AI fast-track)',
      supply: [3.71, 4.10, 4.58, 5.05, 5.55],
      demand: [5.98, 6.32, 6.68, 7.05, 7.45],
      shortfall: [2.27, 2.22, 2.10, 2.00, 1.90],
      gap_2030: 1.90,
    },
  },
};

export interface ConcessionBlock {
  id: string;
  name: string;
  bounds: [[number, number], [number, number]];
  sector: string;
  score: number;
  priority: 'HIGH' | 'MODERATE' | 'LOW';
}

export const FALLBACK_CONCESSION_BLOCKS: ConcessionBlock[] = [
  // Balaghat-Bhandara Mining Sector
  { id: 'BLK-101', name: 'Balaghat Block A',    bounds: [[21.45, 79.50], [21.65, 79.75]], sector: 'Balaghat-Bhandara Mining Sector', score: 0.88, priority: priorityFromProspectivity(0.88) },
  { id: 'BLK-102', name: 'Balaghat Block B',    bounds: [[21.68, 79.70], [21.92, 80.00]], sector: 'Balaghat-Bhandara Mining Sector', score: 0.91, priority: priorityFromProspectivity(0.91) },
  { id: 'BLK-103', name: 'Bhandara Deep Block', bounds: [[21.40, 79.80], [21.60, 80.05]], sector: 'Balaghat-Bhandara Mining Sector', score: 0.74, priority: priorityFromProspectivity(0.74) },

  // Nagpur-Sausar Lease Grid
  { id: 'BLK-104', name: 'Sausar Valley North', bounds: [[21.55, 78.95], [21.80, 79.25]], sector: 'Nagpur-Sausar Lease Grid',        score: 0.82, priority: priorityFromProspectivity(0.82) },
  { id: 'BLK-105', name: 'Nagpur East Sector',  bounds: [[21.30, 79.20], [21.55, 79.48]], sector: 'Nagpur-Sausar Lease Grid',        score: 0.68, priority: priorityFromProspectivity(0.68) },
  { id: 'BLK-106', name: 'Tumsar Concession',   bounds: [[21.35, 79.70], [21.58, 79.98]], sector: 'Nagpur-Sausar Lease Grid',        score: 0.62, priority: priorityFromProspectivity(0.62) },

  // Sandur Mineralized Block
  { id: 'BLK-107', name: 'Sandur West Ridge',   bounds: [[14.90, 76.35], [15.15, 76.60]], sector: 'Sandur Mineralized Block',        score: 0.86, priority: priorityFromProspectivity(0.86) },
  { id: 'BLK-108', name: 'Hospet South Sector', bounds: [[15.12, 76.45], [15.35, 76.72]], sector: 'Sandur Mineralized Block',        score: 0.71, priority: priorityFromProspectivity(0.71) },

  // Keonjhar-Joda Manganese Zone
  { id: 'BLK-109', name: 'Joda Exploration Lease', bounds: [[21.65, 85.10], [21.90, 85.45]], sector: 'Keonjhar-Joda Manganese Zone', score: 0.89, priority: priorityFromProspectivity(0.89) },
  { id: 'BLK-110', name: 'Bonai Extended Block',   bounds: [[21.75, 84.65], [22.00, 85.00]], sector: 'Keonjhar-Joda Manganese Zone', score: 0.73, priority: priorityFromProspectivity(0.73) },

  // Vizianagaram-Srikakulam Concession
  { id: 'BLK-111', name: 'Vizianagaram Sector A',    bounds: [[18.10, 83.25], [18.35, 83.60]], sector: 'Vizianagaram-Srikakulam Concession', score: 0.84, priority: priorityFromProspectivity(0.84) },
  { id: 'BLK-112', name: 'Srikakulam Coastal Strip', bounds: [[18.25, 83.75], [18.50, 84.10]], sector: 'Vizianagaram-Srikakulam Concession', score: 0.66, priority: priorityFromProspectivity(0.66) },

  // Koraput Exploration Sector
  { id: 'BLK-113', name: 'Koraput Valley Sector', bounds: [[18.55, 82.55], [18.85, 82.90]], sector: 'Koraput Exploration Sector', score: 0.78, priority: priorityFromProspectivity(0.78) },
];
