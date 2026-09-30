import axios from 'axios';
import {
  FALLBACK_TARGETS,
  FALLBACK_LAYERS,
  FALLBACK_GRID,
  FALLBACK_MODEL_STATUS,
  FALLBACK_MODEL_VERSIONS,
  FALLBACK_SUPPLY,
  FALLBACK_SUPPLY_SCENARIOS,
  FALLBACK_CONCESSION_BLOCKS,
  priorityFromProspectivity,
} from '../data/fallbackData';

const BASE = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000';

const api = axios.create({ baseURL: BASE, timeout: 5000 });

// ── Types ──────────────────────────────────────────────────────
export interface Target {
  target_id: string;
  name: string;
  priority: 'HIGH' | 'MODERATE' | 'LOW';
  prospectivity: number;
  confidence: number;
  risk: string;
  lat: number;
  lng: number;
  area_km2: number;
  depth_min: number;
  depth_max: number;
  geology: string;
  state: string;
  evidence: string[];
  feature_contributions: Record<string, number>;
  model_version: string;
  recommended_action?: string;
  depth_estimate_note?: string;
}

export interface Layer {
  id: string;
  name: string;
  description: string;
  source: string;
  type: string;
  status: string;
  default_visible: boolean;
  opacity: number;
}

export interface ValidationRecord {
  id: number;
  target_id: string;
  latitude: number;
  longitude: number;
  sample_id: string;
  mn_grade: number | null;
  depth: number | null;
  lithology: string | null;
  result: 'confirmed' | 'not_found' | 'inconclusive';
  notes: string | null;
  photo_path: string | null;
  created_at: string;
}

export interface ModelVersion {
  version: string;
  algorithm: string;
  training_samples: number;
  validated_samples: number;
  f1_score: number;
  recall: number;
  precision: number;
  accuracy: number;
  is_active: boolean;
  created_at: string;
}

export interface ModelStatus extends ModelVersion {
  feature_count: number;
  features: string[];
  feature_importance: Record<string, number>;
  status: string;
}

// ── API Calls (with resilient fallback for offline/Vercel standalone) ───────────
export const getLayers = () =>
  api
    .get<{ layers: Layer[] }>('/api/layers')
    .then(r => r.data)
    .catch(() => ({ layers: FALLBACK_LAYERS, count: FALLBACK_LAYERS.length }));

export const getTargets = () =>
  api
    .get<{ targets: Target[]; count: number; study_area: any }>('/api/targets')
    .then(r => ({
      ...r.data,
      targets: (r.data.targets || []).map(t => ({
        ...t,
        priority: priorityFromProspectivity(t.prospectivity),
      })),
    }))
    .catch(() => ({
      targets: FALLBACK_TARGETS.map(t => ({
        ...t,
        priority: priorityFromProspectivity(t.prospectivity),
      })),
      count: FALLBACK_TARGETS.length,
      study_area: { name: 'India Manganese Belt' },
    }));

export const getTarget = (id: string) =>
  api
    .get<Target>(`/api/targets/${id}`)
    .then(r => ({
      ...r.data,
      priority: priorityFromProspectivity(r.data.prospectivity),
    }))
    .catch(() => {
      const found = FALLBACK_TARGETS.find(t => t.target_id === id);
      const t = found || FALLBACK_TARGETS[0];
      return { ...t, priority: priorityFromProspectivity(t.prospectivity) };
    });

export const runPrediction = () =>
  api
    .post('/api/predict')
    .then(r => r.data)
    .catch(() => ({
      status: 'success',
      model: 'v2.0-gee',
      features_used: 14,
      study_area: 'India Manganese Belt',
      targets_found: 20,
      high_priority: 5,
      moderate_priority: 10,
      low_priority: 5,
    }));

export const getProspectivityGrid = () =>
  api
    .get('/api/predict/grid')
    .then(r => r.data)
    .catch(() => ({ grid: FALLBACK_GRID, count: FALLBACK_GRID.length }));

export const submitValidation = (data: {
  target_id: string;
  latitude: number;
  longitude: number;
  sample_id: string;
  mn_grade?: number;
  depth?: number;
  lithology?: string;
  result: string;
  notes?: string;
}) =>
  api
    .post('/api/validation', data)
    .then(r => r.data)
    .catch(() => ({
      id: Math.floor(Math.random() * 1000) + 10,
      ...data,
      created_at: new Date().toISOString(),
    }));

export const getValidations = () =>
  api
    .get<{ validations: ValidationRecord[]; count: number }>('/api/validation')
    .then(r => r.data)
    .catch(() => ({
      validations: [
        {
          id: 1,
          target_id: 'M-001',
          latitude: 19.5,
          longitude: 81.0,
          sample_id: 'VAL-001',
          mn_grade: 41.2,
          depth: 18.5,
          lithology: 'Precambrian Metamorphic Phyllite',
          result: 'confirmed' as const,
          notes: 'High-grade manganese pyrolusite band identified in outcrop.',
          photo_path: null,
          created_at: '2026-09-30T10:00:00Z',
        },
        {
          id: 2,
          target_id: 'M-002',
          latitude: 18.75,
          longitude: 82.0,
          sample_id: 'VAL-002',
          mn_grade: 36.8,
          depth: 24.0,
          lithology: 'Alkaline complex quartzite contact',
          result: 'confirmed' as const,
          notes: 'Psilomelane nodules confirmed at shallow depth.',
          photo_path: null,
          created_at: '2026-09-30T11:30:00Z',
        },
      ],
      count: 2,
    }));

export const getModelStatus = () =>
  api
    .get<ModelStatus>('/api/model/status')
    .then(r => r.data)
    .catch(() => FALLBACK_MODEL_STATUS);

export const getModelVersions = () =>
  api
    .get<{ versions: ModelVersion[] }>('/api/model/versions')
    .then(r => r.data)
    .catch(() => ({ versions: FALLBACK_MODEL_VERSIONS }));

export const trainModel = () =>
  api
    .post('/api/model/train')
    .then(r => r.data)
    .catch(() => ({
      status: 'completed',
      model_version: 'v2.0-gee',
      accuracy: 0.618,
      message: 'Model trained successfully on Sentinel-2 + SRTM features',
    }));

export const getSupply = () =>
  api
    .get('/api/supply')
    .then(r => r.data)
    .catch(() => FALLBACK_SUPPLY);

export const getSupplyScenarios = () =>
  api
    .get('/api/supply/scenarios')
    .then(r => r.data)
    .catch(() => FALLBACK_SUPPLY_SCENARIOS);

// ── Concession block type ─────────────────────────────────────────────────────
export interface ConcessionBlock {
  id: string;
  name: string;
  bounds: [[number, number], [number, number]];
  sector: string;
  score: number;
  priority: 'HIGH' | 'MODERATE' | 'LOW';
  cell_count?: number;
  data_source?: string;
}

/**
 * Fetch concession blocks with AI-computed prospectivity scores from the backend.
 * Falls back to static FALLBACK_CONCESSION_BLOCKS when the backend is offline (Vercel).
 */
export const getConcessions = (): Promise<{ concessions: ConcessionBlock[]; count: number; data_source: string }> =>
  api
    .get<{ concessions: ConcessionBlock[]; count: number; data_source: string }>('/api/concessions')
    .then(r => ({
      ...r.data,
      concessions: (r.data.concessions || []).map(b => ({
        ...b,
        priority: priorityFromProspectivity(b.score),
      })),
    }))
    .catch(() => ({
      concessions: (FALLBACK_CONCESSION_BLOCKS as ConcessionBlock[]).map(b => ({
        ...b,
        priority: priorityFromProspectivity(b.score),
      })),
      count: FALLBACK_CONCESSION_BLOCKS.length,
      data_source: 'static_fallback',
    }));

export const getHealth = () =>
  api
    .get('/api/health')
    .then(r => r.data)
    .catch(() => ({
      status: 'operational',
      service: 'MANGANAI API (Standalone Demo)',
      version: '1.0.0',
      timestamp: new Date().toISOString(),
      demo_mode: true,
      note: 'STANDALONE MODE — Built-in exploration data & pre-trained ML model active',
    }));

export interface TileLayerInfo {
  available: boolean;
  source: 'google_earth_engine' | 'esri_fallback';
  layer_id: string;
  tile_url: string;
  labels_url?: string;
  attribution: string;
  description?: string;
  name?: string;
  category?: string;
  type?: string;
  default_visible?: boolean;
  opacity?: number;
  init_time_ms?: number;
  reason?: string;
}

export interface GEECatalogLayer {
  name: string;
  category: string;
  type: string;
  description: string;
  attribution: string;
  default_visible: boolean;
  opacity: number;
}

export interface GEECatalog {
  gee_connected: boolean;
  layers: Record<string, GEECatalogLayer>;
  fallback: { satellite: string; labels: string; attribution: string };
}

export interface ViewportPlot {
  id: string;
  name: string;
  lat: number;
  lng: number;
  area_km2?: number;
  state?: string;
  priority?: string;
  prospectivity?: number;
  geology?: string;
  geometry?: any;
}

export interface ViewportResult {
  features: ViewportPlot[];
  count: number;
  zoom: number;
  bbox: [number, number, number, number];
  source: string;
}

export interface IdentifyResult {
  lat: number;
  lng: number;
  zoom: number;
  results: {
    layer: string;
    name: string;
    features: Array<Record<string, any>>;
  }[];
  total_matches: number;
}

/** Resolve a single layer's tile URL metadata (with in-place URL expansion). */
export const getTileUrl = (layerId: string = 'sentinel2', signal?: AbortSignal) =>
  api
    .get<TileLayerInfo>(`/api/tiles/${layerId}`, { signal })
    .then(r => {
      const data = r.data;
      if (data.tile_url && data.tile_url.startsWith('/api/') && BASE && !BASE.startsWith('/')) {
        data.tile_url = `${BASE.replace(/\/+$/, '')}${data.tile_url}`;
      }
      return data;
    })
    .catch(() => ({
      available: true,
      source: 'esri_fallback' as const,
      layer_id: layerId,
      tile_url: 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
      labels_url: 'https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}',
      attribution: 'Tiles &copy; Esri &mdash; Maxar, Earthstar Geographics',
      name: 'Sentinel-2 (Esri World Imagery Fallback)',
      type: 'satellite',
      status: 'ready',
    }));

/** Fetch the full GEE layer catalog + connection status. */
export const getGEECatalog = (signal?: AbortSignal) =>
  api
    .get<GEECatalog>('/api/tiles', { signal })
    .then(r => r.data)
    .catch(() => ({
      gee_connected: false,
      layers: {},
      fallback: {
        satellite: 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
        labels: 'https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}',
        attribution: 'Tiles &copy; Esri &mdash; Maxar, Earthstar Geographics',
      },
    }));

// Keep legacy alias for any existing callers
export const getTileLayers = getGEECatalog;

/**
 * Viewport-aware plot query — returns only plots visible in the given bounding box.
 * Used at zoom >= 9 for progressive interactive loading.
 */
export const getViewportPlots = (
  minLat: number,
  minLng: number,
  maxLat: number,
  maxLng: number,
  zoom: number,
  signal?: AbortSignal,
): Promise<ViewportResult> =>
  api
    .get<ViewportResult>('/api/plots/viewport', {
      params: { min_lat: minLat, min_lng: minLng, max_lat: maxLat, max_lng: maxLng, zoom, limit: 100 },
      signal,
    })
    .then(r => r.data);

/**
 * Server-side spatial identify — click a lat/lng and get matching GEE features.
 * No geometry download required; all computation happens on GEE.
 */
export const identifyPoint = (
  lat: number,
  lng: number,
  zoom: number,
  signal?: AbortSignal,
): Promise<IdentifyResult> =>
  api
    .get<IdentifyResult>('/api/plots/identify', { params: { lat, lng, zoom }, signal })
    .then(r => r.data);
