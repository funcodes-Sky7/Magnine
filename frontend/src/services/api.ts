import axios from 'axios';

const BASE = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000';

const api = axios.create({ baseURL: BASE });

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

// ── API Calls ──────────────────────────────────────────────────
export const getLayers = () => api.get<{ layers: Layer[] }>('/api/layers').then(r => r.data);

export const getTargets = () => api.get<{ targets: Target[]; count: number; study_area: any }>('/api/targets').then(r => r.data);

export const getTarget = (id: string) => api.get<Target>(`/api/targets/${id}`).then(r => r.data);

export const runPrediction = () => api.post('/api/predict').then(r => r.data);

export const getProspectivityGrid = () => api.get('/api/predict/grid').then(r => r.data);

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
}) => api.post('/api/validation', data).then(r => r.data);

export const getValidations = () => api.get<{ validations: ValidationRecord[]; count: number }>('/api/validation').then(r => r.data);

export const getModelStatus = () => api.get<ModelStatus>('/api/model/status').then(r => r.data);

export const getModelVersions = () => api.get<{ versions: ModelVersion[] }>('/api/model/versions').then(r => r.data);

export const trainModel = () => api.post('/api/model/train').then(r => r.data);

export const getSupply = () => api.get('/api/supply').then(r => r.data);

export const getSupplyScenarios = () => api.get('/api/supply/scenarios').then(r => r.data);

export const getHealth = () => api.get('/api/health').then(r => r.data);

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
  api.get<TileLayerInfo>(`/api/tiles/${layerId}`, { signal }).then(r => {
    const data = r.data;
    if (data.tile_url && data.tile_url.startsWith('/api/') && BASE && !BASE.startsWith('/')) {
      data.tile_url = `${BASE.replace(/\/+$/, '')}${data.tile_url}`;
    }
    return data;
  });

/** Fetch the full GEE layer catalog + connection status. */
export const getGEECatalog = (signal?: AbortSignal) =>
  api.get<GEECatalog>('/api/tiles', { signal }).then(r => r.data);

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
