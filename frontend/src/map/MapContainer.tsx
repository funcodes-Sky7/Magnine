/**
 * MANGANAI MapContainer — Production GEE Map Component
 *
 * Architecture:
 *  - ALL raster/vector rendering goes through the backend tile proxy (/api/tiles/{layer_id}/{z}/{x}/{y})
 *  - No FeatureCollections are downloaded to the browser
 *  - At zoom >= 9, progressive viewport queries fetch only visible plot metadata
 *  - Click-to-identify calls the backend spatial API (no geometry required client-side)
 *  - mousemove is throttled to avoid React re-renders at 60fps
 *  - Each layer is lazily initialized and cached for the session
 */
import { useState, useEffect, useRef, useCallback } from 'react';
import {
  MapContainer as LeafletMap,
  TileLayer,
  CircleMarker,
  Rectangle,
  Tooltip,
  useMap,
  ZoomControl,
} from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import L from './leaflet-setup';
import type { Target, TileLayerInfo, ViewportPlot, IdentifyResult, ConcessionBlock } from '../services/api';
import {
  getTileUrl,
  getViewportPlots,
  identifyPoint,
  getGEECatalog,
  getConcessions,
  type GEECatalog,
} from '../services/api';
import { FALLBACK_OCCURRENCES, priorityFromProspectivity } from '../data/fallbackData';

// Fix leaflet icon paths
delete (L.Icon.Default.prototype as any)._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon-2x.png',
  iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png',
});

// ── Constants ───────────────────────────────────────────────────────────────
const CENTER: [number, number] = [20.5, 80.5];
// Vite proxies /api/* to the backend — use relative paths in development.
// In production, VITE_API_BASE_URL must be set to the full backend host.
const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? '';

const ESRI_FALLBACK_URL =
  'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}';
const ESRI_LABELS_URL =
  'https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}';
const ESRI_ATTRIBUTION =
  'Tiles &copy; Esri &mdash; Source: Esri, Maxar, Earthstar Geographics';

/** Zoom level below which only server tiles are shown (no viewport queries) */
const VIEWPORT_ZOOM_THRESHOLD = 9;
/** Debounce delay for viewport changes (ms) */
const VIEWPORT_DEBOUNCE_MS = 350;
/** Throttle delay for mousemove coordinate updates (ms) */
const COORDS_THROTTLE_MS = 80;

// ── Session-level caches ────────────────────────────────────────────────────
/** Tile metadata cache — GEE map IDs are valid for ~1 hour */
const tileMetaCache = new Map<string, TileLayerInfo>();
/** GEE catalog cache */
let catalogCache: GEECatalog | null = null;

// ── Layer definitions (UI) ──────────────────────────────────────────────────
const LAYER_GROUPS = [
  {
    group: '🛰️ Satellite Imagery',
    layers: [
      { id: 'sentinel2', label: 'Sentinel-2 True Color', shortLabel: 'RGB', isBasemap: true },
      { id: 'sentinel2_falsecolor', label: 'NIR False Color', shortLabel: 'NIR', isBasemap: true },
      { id: 'sentinel2_femn', label: 'Fe-Mn Index', shortLabel: 'Fe-Mn', isBasemap: false },
    ],
  },
  {
    group: '⛰️ Terrain',
    layers: [
      { id: 'dem', label: 'Elevation (SRTM 30m)', shortLabel: 'DEM', isBasemap: false },
      { id: 'landcover', label: 'ESA Land Cover', shortLabel: 'LULC', isBasemap: false },
    ],
  },
  {
    group: '🪨 Geology',
    layers: [
      { id: 'geology', label: 'Geological Formations', shortLabel: 'Geology', isBasemap: false },
      { id: 'faults', label: 'Faults & Shear Zones', shortLabel: 'Faults', isBasemap: false },
    ],
  },
  {
    group: '🏭 Concessions',
    layers: [
      { id: 'plots', label: 'Exploration Blocks', shortLabel: 'Blocks', isBasemap: false },
      { id: 'occurrences', label: 'Mn Mines & Occurrences', shortLabel: 'Mines', isBasemap: false },
    ],
  },
];

const ALL_LAYER_IDS = LAYER_GROUPS.flatMap(g => g.layers.map(l => l.id));
const BASEMAP_IDS = LAYER_GROUPS.flatMap(g => g.layers.filter(l => l.isBasemap).map(l => l.id));

// ── Props ───────────────────────────────────────────────────────────────────
interface Props {
  targets: Target[];
  /** legacy visibility map from Exploration.tsx (keys: 'occurrences', 'prospectivity', etc.) */
  layers: Record<string, boolean>;
  onTargetClick: (t: Target) => void;
  selectedTarget: Target | null;
  prospectivityGrid: Array<{ lat: number; lng: number; prospectivity: number }>;
  onCoordsChange?: (coords: string) => void;
}

// ── Sub-components ──────────────────────────────────────────────────────────

/**
 * GEETileLayer — wraps a single TileLayer that is initialized lazily.
 * Shows a loading indicator while fetching tile metadata.
 */
function GEETileLayer({
  layerId,
  opacity,
  visible,
}: {
  layerId: string;
  opacity: number;
  visible: boolean;
}) {
  const [info, setInfo] = useState<TileLayerInfo | null>(() => tileMetaCache.get(layerId) ?? null);
  const [loading, setLoading] = useState(!tileMetaCache.has(layerId));
  const fetchedRef = useRef(false);

  useEffect(() => {
    if (!visible) return; // Don't initialize if layer is off
    if (tileMetaCache.has(layerId)) {
      setInfo(tileMetaCache.get(layerId)!);
      setLoading(false);
      return;
    }
    if (fetchedRef.current) return;
    fetchedRef.current = true;

    const ac = new AbortController();
    setLoading(true);
    getTileUrl(layerId, ac.signal)
      .then(data => {
        if (ac.signal.aborted) return;
        tileMetaCache.set(layerId, data);
        setInfo(data);
      })
      .catch(() => {
        if (ac.signal.aborted) return;
        // Graceful degradation — store fallback so we don't retry
        const fallback: TileLayerInfo = {
          available: false,
          source: 'esri_fallback',
          layer_id: layerId,
          tile_url: ESRI_FALLBACK_URL,
          attribution: ESRI_ATTRIBUTION,
        };
        tileMetaCache.set(layerId, fallback);
        setInfo(fallback);
      })
      .finally(() => {
        if (!ac.signal.aborted) setLoading(false);
      });
    return () => ac.abort();
  }, [layerId, visible]);

  if (!visible || !info) return null;

  const isLocalApi = Boolean(info.tile_url && info.tile_url.startsWith('/api/'));
  const url = isLocalApi
    ? (BASE_URL && !BASE_URL.startsWith('/') ? `${BASE_URL.replace(/\/+$/, '')}${info.tile_url}` : ESRI_FALLBACK_URL)
    : (info.tile_url || ESRI_FALLBACK_URL);

  return (
    <TileLayer
      key={`${layerId}-${url}`}
      url={url}
      attribution={info.attribution}
      opacity={opacity}
      maxZoom={20}
      maxNativeZoom={info.available ? 18 : 17}
      errorTileUrl="data:image/gif;base64,R0lGODlhAQABAIAAAP///wAAACH5BAEAAAAALAAAAAABAAEAAAICRAEAOw=="
    />
  );
}

/**
 * ViewportPlotLayer — shows lightweight outline markers for plots visible in the
 * current viewport. Only active at zoom >= VIEWPORT_ZOOM_THRESHOLD.
 * Does NOT download the full FeatureCollection.
 */
function ViewportPlotLayer({
  visible,
  onPlotClick,
}: {
  visible: boolean;
  onPlotClick?: (plot: ViewportPlot) => void;
}) {
  const map = useMap();
  const [plots, setPlots] = useState<ViewportPlot[]>([]);
  const abortRef = useRef<AbortController | null>(null);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const fetchPlots = useCallback(() => {
    const zoom = map.getZoom();
    if (!visible || zoom < VIEWPORT_ZOOM_THRESHOLD) {
      setPlots([]);
      return;
    }

    const bounds = map.getBounds();
    const minLat = bounds.getSouth();
    const minLng = bounds.getWest();
    const maxLat = bounds.getNorth();
    const maxLng = bounds.getEast();

    // Cancel previous in-flight request
    if (abortRef.current) abortRef.current.abort();
    const ac = new AbortController();
    abortRef.current = ac;

    getViewportPlots(minLat, minLng, maxLat, maxLng, zoom, ac.signal)
      .then(result => {
        if (ac.signal.aborted) return;
        setPlots(result.features || []);
      })
      .catch(() => {
        if (!ac.signal.aborted) setPlots([]);
      });
  }, [map, visible]);

  // Debounced viewport event handler
  const handleViewChange = useCallback(() => {
    if (timerRef.current) clearTimeout(timerRef.current);
    timerRef.current = setTimeout(fetchPlots, VIEWPORT_DEBOUNCE_MS);
  }, [fetchPlots]);

  useEffect(() => {
    map.on('moveend', handleViewChange);
    map.on('zoomend', handleViewChange);
    // Initial fetch
    handleViewChange();
    return () => {
      map.off('moveend', handleViewChange);
      map.off('zoomend', handleViewChange);
      if (timerRef.current) clearTimeout(timerRef.current);
      if (abortRef.current) abortRef.current.abort();
    };
  }, [map, handleViewChange]);

  // Also re-fetch when visibility changes
  useEffect(() => {
    handleViewChange();
  }, [visible, handleViewChange]);

  if (!visible) return null;

  return (
    <>
      {plots.map(plot => {
        const plotPrio = plot.priority || (plot.prospectivity !== undefined ? priorityFromProspectivity(plot.prospectivity) : 'MODERATE');
        return (
          <CircleMarker
            key={plot.id}
            center={[plot.lat, plot.lng]}
            radius={5}
            fillColor={plotPrio === 'HIGH' ? '#22c55e' : plotPrio === 'MODERATE' ? '#f59e0b' : '#94a3b8'}
            fillOpacity={0.75}
            color="#ffffff"
            weight={1.5}
            eventHandlers={{ click: () => onPlotClick?.(plot) }}
          >
          <Tooltip direction="top" offset={[0, -8]} opacity={0.95}>
            <div style={{ fontFamily: 'Inter,sans-serif', minWidth: 120 }}>
              <div style={{ fontSize: 10, color: '#94a3b8', fontWeight: 600 }}>{plot.id}</div>
              <div style={{ fontSize: 12, fontWeight: 700, marginTop: 2 }}>{plot.name}</div>
              {plot.state && (
                <div style={{ fontSize: 10, color: '#64748b', marginTop: 2 }}>{plot.state}</div>
              )}
            </div>
          </Tooltip>
        </CircleMarker>
        );
      })}
    </>
  );
}

/**
 * MapController — handles:
 * - map size invalidation on resize / ResizeObserver
 * - fly-to on selectedTarget change
 * - throttled mousemove → coordinate readout (does NOT trigger React re-render every frame)
 * - click-to-identify: sends coordinate to backend, receives spatial features
 */
function MapController({
  selectedTarget,
  onCoordsChange,
  onIdentify,
  identifyEnabled,
}: {
  selectedTarget: Target | null;
  onCoordsChange?: (c: string) => void;
  onIdentify?: (result: IdentifyResult | null, loading: boolean) => void;
  identifyEnabled: boolean;
}) {
  const map = useMap();
  const lastCoordsRef = useRef('');
  const identifyAbortRef = useRef<AbortController | null>(null);

  // Map size fix on resize
  useEffect(() => {
    const onResize = () => map.invalidateSize();
    window.addEventListener('resize', onResize);

    let ro: ResizeObserver | null = null;
    const container = map.getContainer();
    if (typeof ResizeObserver !== 'undefined' && container) {
      ro = new ResizeObserver(() => map.invalidateSize());
      ro.observe(container);
    }
    const t = setTimeout(() => map.invalidateSize(), 200);

    return () => {
      window.removeEventListener('resize', onResize);
      if (ro) ro.disconnect();
      clearTimeout(t);
    };
  }, [map]);

  // Fly to selected target
  useEffect(() => {
    if (selectedTarget) {
      map.flyTo([selectedTarget.lat, selectedTarget.lng], 10, { duration: 1.5 });
    }
  }, [selectedTarget, map]);

  // Throttled mousemove (does NOT setState — writes directly to DOM via callback)
  useEffect(() => {
    if (!onCoordsChange) return;
    let lastFire = 0;
    const handleMove = (e: L.LeafletMouseEvent) => {
      const now = Date.now();
      if (now - lastFire < COORDS_THROTTLE_MS) return;
      lastFire = now;
      const coords = `${e.latlng.lat.toFixed(4)}°N, ${e.latlng.lng.toFixed(4)}°E`;
      if (coords !== lastCoordsRef.current) {
        lastCoordsRef.current = coords;
        onCoordsChange(coords);
      }
    };
    map.on('mousemove', handleMove);
    return () => { map.off('mousemove', handleMove); };
  }, [map, onCoordsChange]);

  // Click-to-identify
  useEffect(() => {
    if (!identifyEnabled || !onIdentify) return;

    const handleClick = (e: L.LeafletMouseEvent) => {
      const { lat, lng } = e.latlng;
      const zoom = map.getZoom();

      // Cancel any previous identify request
      if (identifyAbortRef.current) identifyAbortRef.current.abort();
      const ac = new AbortController();
      identifyAbortRef.current = ac;

      onIdentify(null, true); // signal loading

      identifyPoint(lat, lng, zoom, ac.signal)
        .then(result => {
          if (ac.signal.aborted) return;
          onIdentify(result, false);
        })
        .catch(err => {
          if (!ac.signal.aborted) {
            console.warn('[MapController] identify error:', err);
            onIdentify(null, false);
          }
        });
    };

    map.on('click', handleClick);
    return () => {
      map.off('click', handleClick);
      if (identifyAbortRef.current) identifyAbortRef.current.abort();
    };
  }, [map, identifyEnabled, onIdentify]);

  return null;
}

// ── Main export ─────────────────────────────────────────────────────────────
export default function MapContainer({
  targets,
  layers: legacyLayers,
  onTargetClick,
  selectedTarget,
  prospectivityGrid: _grid,
  onCoordsChange,
}: Props) {
  // ── Layer visibility state (independent per layer) ──────────────────────
  const [layerVisibility, setLayerVisibility] = useState<Record<string, boolean>>(() => ({
    sentinel2: true,
    sentinel2_falsecolor: false,
    sentinel2_femn: false,
    dem: false,
    landcover: false,
    plots: true,
    geology: false,
    faults: false,
    occurrences: true,
  }));
  const [layerOpacity, setLayerOpacity] = useState<Record<string, number>>(() => ({
    sentinel2: 1.0,
    sentinel2_falsecolor: 0.85,
    sentinel2_femn: 0.75,
    dem: 0.6,
    landcover: 0.5,
    plots: 0.9,
    geology: 0.7,
    faults: 0.9,
    occurrences: 0.95,
  }));

  // ── Concession blocks (AI-scored, loaded from backend, fallback to static) ─
  const [concessionBlocks, setConcessionBlocks] = useState<ConcessionBlock[]>([]);
  const [concessionsDataSource, setConcessionsDataSource] = useState<string>('loading');

  useEffect(() => {
    getConcessions().then(res => {
      setConcessionBlocks(res.concessions);
      setConcessionsDataSource(res.data_source);
    });
  }, []);

  // ── GEE connection status ────────────────────────────────────────────────
  const [geeConnected, setGeeConnected] = useState<boolean | null>(null);

  // ── Identify state ───────────────────────────────────────────────────────
  const [identifyResult, setIdentifyResult] = useState<IdentifyResult | null>(null);
  const [identifyLoading, setIdentifyLoading] = useState(false);
  const [identifyPos, setIdentifyPos] = useState<{ lat: number; lng: number } | null>(null);
  const [identifyEnabled, setIdentifyEnabled] = useState(true);

  // ── Active basemap (only one can be primary satellite layer) ─────────────
  const [activeBasemap, setActiveBasemap] = useState('sentinel2');

  // Fetch catalog on mount for GEE status
  useEffect(() => {
    const ac = new AbortController();
    getGEECatalog(ac.signal)
      .then(catalog => { if (!ac.signal.aborted) setGeeConnected(catalog.gee_connected); })
      .catch(() => { if (!ac.signal.aborted) setGeeConnected(false); });
    return () => ac.abort();
  }, []);

  const handleIdentify = useCallback(
    (result: IdentifyResult | null, loading: boolean) => {
      setIdentifyLoading(loading);
      if (result) {
        setIdentifyResult(result);
        setIdentifyPos({ lat: result.lat, lng: result.lng });
        // If there's a matching target-like feature, notify the parent
        const plotResult = result.results?.find(r =>
          r.layer === 'plots' || r.layer === 'occurrences'
        );
        if (plotResult && plotResult.features.length > 0) {
          const feat = plotResult.features[0];
          // Map to Target shape for drawer
          const pseudoTarget: Target = {
            target_id: String(feat.id || feat.plot_id || feat.name || 'GEE-Feature'),
            name: feat.name || feat.label || feat.type || 'GEE Feature',
            priority: priorityFromProspectivity(feat.prospectivity ?? 0.5),
            prospectivity: feat.prospectivity ?? 0.5,
            confidence: feat.confidence ?? 0.5,
            risk: feat.risk || 'Moderate',
            lat: result.lat,
            lng: result.lng,
            area_km2: feat.area_km2 ?? 0,
            depth_min: feat.depth_min ?? 0,
            depth_max: feat.depth_max ?? 0,
            geology: feat.geology || plotResult.name,
            state: feat.state || '',
            evidence: feat.evidence || [],
            feature_contributions: feat.feature_contributions || {},
            model_version: feat.model_version || 'GEE Spatial Query',
            recommended_action: feat.recommended_action || 'Further investigation recommended',
          };
          onTargetClick(pseudoTarget);
        }
      }
    },
    [onTargetClick],
  );

  const toggleLayer = (id: string) => {
    // Basemap layers are mutually exclusive
    if (BASEMAP_IDS.includes(id)) {
      setActiveBasemap(id);
      setLayerVisibility(v => {
        const next = { ...v };
        BASEMAP_IDS.forEach(bid => { next[bid] = false; });
        next[id] = true;
        return next;
      });
    } else {
      setLayerVisibility(v => ({ ...v, [id]: !v[id] }));
    }
  };

  const isGEE = geeConnected === true;
  const statusLabel =
    geeConnected === null
      ? '⏳ Connecting to GEE…'
      : geeConnected
        ? '🛰️ Google Earth Engine'
        : '🗺️ Esri Fallback';

  return (
    <div style={{ width: '100%', height: '100%', position: 'relative', background: '#0F172A' }}>
      <LeafletMap
        center={CENTER}
        zoom={6}
        style={{ width: '100%', height: '100%' }}
        zoomControl={false}
      >
        {/* Solid fallback satellite basemap — guarantees map is never blank */}
        <TileLayer
          url={ESRI_FALLBACK_URL}
          attribution={ESRI_ATTRIBUTION}
          maxZoom={20}
        />

        {/* ── Raster basemap layers (only active one rendered) ── */}
        {BASEMAP_IDS.map(id => (
          <GEETileLayer
            key={id}
            layerId={id}
            visible={layerVisibility[id] === true}
            opacity={layerOpacity[id] ?? 1.0}
          />
        ))}

        {/* Fe-Mn computed index overlay (can be on top of any basemap) */}
        <GEETileLayer
          layerId="sentinel2_femn"
          visible={layerVisibility['sentinel2_femn'] === true}
          opacity={layerOpacity['sentinel2_femn'] ?? 0.75}
        />

        {/* ── Terrain layers ── */}
        <GEETileLayer
          layerId="dem"
          visible={layerVisibility['dem'] === true}
          opacity={layerOpacity['dem'] ?? 0.6}
        />
        <GEETileLayer
          layerId="landcover"
          visible={layerVisibility['landcover'] === true}
          opacity={layerOpacity['landcover'] ?? 0.5}
        />

        {/* ── Geology vector layers (rasterized by GEE fc.style()) ── */}
        <GEETileLayer
          layerId="geology"
          visible={layerVisibility['geology'] === true}
          opacity={layerOpacity['geology'] ?? 0.7}
        />
        <GEETileLayer
          layerId="faults"
          visible={layerVisibility['faults'] === true}
          opacity={layerOpacity['faults'] ?? 0.9}
        />

        {/* ── Concession / plot layers ── */}
        <GEETileLayer
          layerId="plots"
          visible={layerVisibility['plots'] === true}
          opacity={layerOpacity['plots'] ?? 0.9}
        />
        <GEETileLayer
          layerId="occurrences"
          visible={layerVisibility['occurrences'] === true}
          opacity={layerOpacity['occurrences'] ?? 0.95}
        />

        {/* Reference labels always on top */}
        <TileLayer
          url={ESRI_LABELS_URL}
          attribution=""
          maxZoom={20}
          opacity={0.7}
        />

        {/* Viewport-progressive plot markers (zoom >= 9 only) */}
        <ViewportPlotLayer
          visible={layerVisibility['plots'] === true}
          onPlotClick={plot => {
            // Convert viewport plot to Target-like for drawer
            const pseudoTarget: Target = {
              target_id: plot.id,
              name: plot.name,
              priority: priorityFromProspectivity(plot.prospectivity ?? 0.5),
              prospectivity: plot.prospectivity ?? 0.5,
              confidence: 0.7,
              risk: 'Moderate',
              lat: plot.lat,
              lng: plot.lng,
              area_km2: plot.area_km2 ?? 0,
              depth_min: 0,
              depth_max: 0,
              geology: plot.geology || '',
              state: plot.state || '',
              evidence: [],
              feature_contributions: {},
              model_version: 'Viewport Query',
            };
            onTargetClick(pseudoTarget);
          }}
        />

        {/* ── Square / Rectangular Concession Lease Blocks (AI-scored) ── */}
        {layerVisibility['plots'] === true &&
          concessionBlocks.map(block => {
            const prio = priorityFromProspectivity(block.score);
            const isHigh = prio === 'HIGH';
            const isMod = prio === 'MODERATE';
            const borderColor = isHigh ? '#16A34A' : isMod ? '#EA580C' : '#64748B';
            const fillColor   = isHigh ? '#22C55E' : isMod ? '#FB923C' : '#94A3B8';
            return (
              <Rectangle
                key={`concession-${block.id}`}
                bounds={block.bounds}
                pathOptions={{
                  color: borderColor,
                  weight: 2,
                  dashArray: '5, 5',
                  fillColor: fillColor,
                  fillOpacity: 0.16,
                }}
              >
                <Tooltip direction="center" permanent={false} opacity={0.95}>
                  <div style={{ fontFamily: 'Inter, sans-serif', padding: '2px 4px', minWidth: 170 }}>
                    <div style={{ fontSize: 10, color: borderColor, fontWeight: 700, letterSpacing: '0.05em' }}>
                      CONCESSION LEASE BLOCK
                    </div>
                    <div style={{ fontSize: 13, fontWeight: 700, margin: '2px 0' }}>{block.name}</div>
                    <div style={{ fontSize: 11, color: '#334155' }}>{block.sector}</div>
                    <div style={{ display: 'flex', gap: 10, marginTop: 4, alignItems: 'center' }}>
                      <span style={{ fontSize: 12, fontWeight: 700, color: borderColor }}>
                        {(block.score * 100).toFixed(0)}% prospectivity
                      </span>
                      <span style={{
                        fontSize: 10, fontWeight: 700, padding: '1px 6px',
                        borderRadius: 4, background: borderColor, color: '#fff',
                      }}>
                        {prio}
                      </span>
                    </div>
                    {block.cell_count !== undefined && (
                      <div style={{ fontSize: 10, color: '#64748B', marginTop: 2 }}>
                        Avg of {block.cell_count} grid cell{block.cell_count !== 1 ? 's' : ''}
                        {concessionsDataSource === 'real_ml_predictions' ? ' · GEE ML Model' : ' · Demo data'}
                      </div>
                    )}
                  </div>
                </Tooltip>
              </Rectangle>
            );
          })}

        {/* ── Exploration Target Square Footprint Boxes ── */}
        {layerVisibility['plots'] === true &&
          targets.map(target => {
            const radius_km = Math.sqrt((target.area_km2 || 60) / Math.PI);
            const dLat = radius_km / 111;
            const dLng = radius_km / (111 * Math.cos((target.lat * Math.PI) / 180));
            const prio = priorityFromProspectivity(target.prospectivity);
            const isHigh = prio === 'HIGH';
            const isMod = prio === 'MODERATE';
            const isSelected = selectedTarget?.target_id === target.target_id;
            const strokeColor = isSelected ? '#3B82F6' : isHigh ? '#16A34A' : isMod ? '#EA580C' : '#64748B';
            const fillColor = isHigh ? '#22C55E' : isMod ? '#FB923C' : '#94A3B8';

            return (
              <Rectangle
                key={`target-box-${target.target_id}`}
                bounds={[
                  [target.lat - dLat, target.lng - dLng],
                  [target.lat + dLat, target.lng + dLng],
                ]}
                pathOptions={{
                  color: strokeColor,
                  weight: isSelected ? 3 : 2,
                  dashArray: '4, 4',
                  fillColor: fillColor,
                  fillOpacity: isSelected ? 0.28 : 0.14,
                }}
                eventHandlers={{ click: () => onTargetClick(target) }}
              />
            );
          })}

        {/* ── Known Manganese Mines & Deposits (RED Circles) ── */}
        {layerVisibility['occurrences'] === true &&
          FALLBACK_OCCURRENCES.map(occ => {
            const isSelected = selectedTarget?.target_id === occ.id;
            return (
              <CircleMarker
                key={occ.id}
                center={[occ.lat, occ.lng]}
                radius={isSelected ? 10 : 7}
                fillColor="#DC2626"
                fillOpacity={0.95}
                color={isSelected ? '#3B82F6' : '#FFFFFF'}
                weight={isSelected ? 3 : 2}
                pane="markerPane"
                eventHandlers={{
                  click: (e) => {
                    L.DomEvent.stopPropagation(e);
                    const pseudoTarget: Target = {
                      target_id: occ.id,
                      name: occ.name,
                      priority: 'HIGH',
                      prospectivity: occ.grade_pct ? Math.min(Number((occ.grade_pct / 50).toFixed(2)), 1.0) : 0.85,
                      confidence: 0.95,
                      risk: 'Low - Verified Deposit',
                      lat: occ.lat,
                      lng: occ.lng,
                      area_km2: 25.0,
                      depth_min: 0,
                      depth_max: 60,
                      geology: `${occ.type} Manganese Mineralization`,
                      state: occ.state,
                      evidence: [
                        `Verified Historical Manganese Deposit: ${occ.name} (${occ.id})`,
                        `Assayed Ore Grade: ${occ.grade_pct}% Mn`,
                        `Current Operational Status: ${occ.status}`,
                        `Deposit Classification: ${occ.type}`,
                        `State: ${occ.state}, India`,
                        `Ground-truth verification benchmark for ML prospectivity model`,
                      ],
                      feature_contributions: {
                        geology_score: 0.95,
                        spectral_fe_mn_ratio: 0.90,
                        dist_to_occurrence_km: 1.0,
                      },
                      model_version: 'Geological Survey of India (GSI) Ground Truth',
                      recommended_action: `Verified Reserve (${occ.status}) — Active Production`,
                      depth_estimate_note: `Documented deposit with confirmed ${occ.grade_pct}% Mn mineralization.`,
                    };
                    onTargetClick(pseudoTarget);
                  },
                }}
              >
                <Tooltip direction="top" offset={[0, -10]} opacity={1}>
                  <div style={{ fontFamily: 'Inter, sans-serif', minWidth: 160 }}>
                    <div style={{ fontSize: 10, color: '#DC2626', fontWeight: 700, letterSpacing: '0.05em' }}>
                      HISTORICAL MN DEPOSIT / MINE
                    </div>
                    <div style={{ fontSize: 13, fontWeight: 700, margin: '2px 0' }}>
                      {occ.name}
                    </div>
                    <div style={{ fontSize: 11, color: '#334155' }}>
                      Grade: <b>{occ.grade_pct}% Mn</b> | {occ.state}
                    </div>
                    <div style={{ fontSize: 10, color: '#64748B', marginTop: 2 }}>
                      Status: {occ.status} ({occ.type})
                    </div>
                    <div style={{ fontSize: 10, color: '#DC2626', fontWeight: 600, marginTop: 4 }}>
                      👆 Click to open details
                    </div>
                  </div>
                </Tooltip>
              </CircleMarker>
            );
          })}

        {/* ── AI Exploration Target Markers (Green dots = High, Orange dots = Moderate) ── */}
        {targets.map(target => {
          const prio = priorityFromProspectivity(target.prospectivity);
          const isHigh = prio === 'HIGH';
          const isMod = prio === 'MODERATE';
          const isSelected = selectedTarget?.target_id === target.target_id;
          const fillColor = isHigh ? '#16A34A' : isMod ? '#EA580C' : '#64748B';

          return (
            <CircleMarker
              key={target.target_id}
              center={[target.lat, target.lng]}
              radius={isSelected ? 12 : isHigh ? 8 : isMod ? 7 : 5}
              fillColor={fillColor}
              fillOpacity={0.95}
              color={isSelected ? '#3B82F6' : '#FFFFFF'}
              weight={isSelected ? 3 : 2}
              pane="markerPane"
              eventHandlers={{
                click: (e) => {
                  L.DomEvent.stopPropagation(e);
                  onTargetClick(target);
                },
              }}
            >
              <Tooltip direction="top" offset={[0, -10]} opacity={1}>
                <div style={{ fontFamily: 'Inter, sans-serif', minWidth: 150 }}>
                  <div style={{ fontSize: 10, color: fillColor, fontWeight: 700 }}>
                    {prio} PRIORITY TARGET
                  </div>
                  <div style={{ fontSize: 13, fontWeight: 700, margin: '2px 0' }}>
                    {target.name} ({target.target_id})
                  </div>
                  <div style={{ display: 'flex', gap: 12, marginTop: 4 }}>
                    <span style={{ fontSize: 11 }}>
                      <b>{(target.prospectivity * 100).toFixed(0)}%</b> prospectivity
                    </span>
                    <span style={{ fontSize: 11, color: '#64748B' }}>
                      {target.depth_min}-{target.depth_max}m
                    </span>
                  </div>
                  <div style={{ fontSize: 10, color: '#475569', marginTop: 2 }}>
                    {target.geology} ({target.state})
                  </div>
                </div>
              </Tooltip>
            </CircleMarker>
          );
        })}

        <MapController
          selectedTarget={selectedTarget}
          onCoordsChange={onCoordsChange}
          onIdentify={handleIdentify}
          identifyEnabled={identifyEnabled}
        />

        <ZoomControl position="bottomright" />
      </LeafletMap>

      {/* ── Top-left: GEE status + basemap switcher ── */}
      <div
        style={{
          position: 'absolute',
          top: 14,
          left: 14,
          zIndex: 800,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'flex-start',
          gap: 6,
          pointerEvents: 'none',
        }}
      >
        {/* Status pill */}
        <div
          style={{
            pointerEvents: 'auto',
            background: 'rgba(15, 23, 42, 0.88)',
            color: '#F8FAFC',
            backdropFilter: 'blur(8px)',
            padding: '5px 10px',
            borderRadius: 8,
            fontSize: 12,
            border: isGEE
              ? '1px solid rgba(34, 197, 94, 0.4)'
              : '1px solid rgba(255, 255, 255, 0.12)',
            display: 'flex',
            alignItems: 'center',
            gap: 8,
            boxShadow: '0 4px 12px rgba(0,0,0,0.3)',
          }}
        >
          <span
            style={{
              width: 7,
              height: 7,
              borderRadius: '50%',
              backgroundColor:
                geeConnected === null ? '#F59E0B' : isGEE ? '#22C55E' : '#38BDF8',
              boxShadow:
                geeConnected === null
                  ? '0 0 6px #F59E0B'
                  : isGEE
                    ? '0 0 8px #22C55E'
                    : '0 0 6px #38BDF8',
              display: 'inline-block',
            }}
          />
          <span style={{ fontWeight: 600, fontSize: 11 }}>{statusLabel}</span>
          {identifyLoading && (
            <span
              style={{
                fontSize: 10,
                padding: '2px 6px',
                borderRadius: 4,
                background: 'rgba(245, 158, 11, 0.2)',
                color: '#FDE68A',
                fontWeight: 500,
              }}
            >
              🔍 Identifying…
            </span>
          )}
        </div>

        {/* Basemap quick-switcher */}
        <div
          style={{
            pointerEvents: 'auto',
            background: 'rgba(15, 23, 42, 0.88)',
            backdropFilter: 'blur(8px)',
            padding: '3px',
            borderRadius: 8,
            border: '1px solid rgba(255,255,255,0.1)',
            display: 'flex',
            gap: 3,
            boxShadow: '0 4px 12px rgba(0,0,0,0.25)',
          }}
        >
          {[
            { id: 'sentinel2', label: 'RGB' },
            { id: 'sentinel2_falsecolor', label: 'NIR' },
            { id: 'dem', label: 'DEM' },
            { id: 'landcover', label: 'LULC' },
          ].map(l => {
            const isActive = layerVisibility[l.id];
            const isCached = tileMetaCache.has(l.id);
            return (
              <button
                key={l.id}
                onClick={() => toggleLayer(l.id)}
                title={isCached ? `${l.label} (cached)` : l.label}
                style={{
                  background: isActive ? 'rgba(59,130,246,0.25)' : 'transparent',
                  color: isActive ? '#93C5FD' : '#94A3B8',
                  border: isActive
                    ? '1px solid rgba(59,130,246,0.5)'
                    : '1px solid transparent',
                  padding: '3px 7px',
                  borderRadius: 6,
                  fontSize: 10,
                  fontWeight: isActive ? 600 : 400,
                  cursor: 'pointer',
                  transition: 'all 0.15s ease',
                  position: 'relative',
                }}
              >
                {l.label}
                {isCached && !isActive && (
                  <span
                    style={{
                      position: 'absolute',
                      top: 1,
                      right: 1,
                      width: 3,
                      height: 3,
                      borderRadius: '50%',
                      background: '#22C55E',
                    }}
                  />
                )}
              </button>
            );
          })}
        </div>

        {/* Identify toggle */}
        <button
          onClick={() => setIdentifyEnabled(v => !v)}
          style={{
            pointerEvents: 'auto',
            background: identifyEnabled
              ? 'rgba(59, 130, 246, 0.2)'
              : 'rgba(15, 23, 42, 0.7)',
            color: identifyEnabled ? '#93C5FD' : '#64748B',
            border: identifyEnabled
              ? '1px solid rgba(59,130,246,0.4)'
              : '1px solid rgba(255,255,255,0.08)',
            backdropFilter: 'blur(6px)',
            padding: '4px 9px',
            borderRadius: 7,
            fontSize: 10,
            fontWeight: 600,
            cursor: 'pointer',
            transition: 'all 0.15s',
          }}
          title="Click anywhere on the map to identify GEE features"
        >
          {identifyEnabled ? '🔍 Identify ON' : '🔍 Identify OFF'}
        </button>
      </div>

      {/* ── GEE Layer panel (right side, compact) ── */}
      <div
        style={{
          position: 'absolute',
          top: 14,
          right: 14,
          zIndex: 800,
          width: 210,
          background: 'rgba(15, 23, 42, 0.92)',
          backdropFilter: 'blur(12px)',
          border: '1px solid rgba(255,255,255,0.1)',
          borderRadius: 10,
          boxShadow: '0 8px 24px rgba(0,0,0,0.4)',
          padding: '8px 0',
          maxHeight: 'calc(100vh - 120px)',
          overflowY: 'auto',
          scrollbarWidth: 'thin',
        }}
      >
        <div
          style={{
            padding: '0 10px 6px',
            fontSize: 10,
            fontWeight: 700,
            color: '#64748B',
            letterSpacing: '0.08em',
            textTransform: 'uppercase',
            borderBottom: '1px solid rgba(255,255,255,0.06)',
            marginBottom: 4,
          }}
        >
          GEE Layers
        </div>
        {LAYER_GROUPS.map(group => (
          <div key={group.group} style={{ marginBottom: 4 }}>
            <div
              style={{
                padding: '4px 10px 2px',
                fontSize: 9,
                fontWeight: 600,
                color: '#475569',
                letterSpacing: '0.05em',
              }}
            >
              {group.group}
            </div>
            {group.layers.map(layer => {
              const isOn = layerVisibility[layer.id] === true;
              const isCached = tileMetaCache.has(layer.id);
              return (
                <div
                  key={layer.id}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: 6,
                    padding: '3px 10px',
                    cursor: 'pointer',
                    borderRadius: 4,
                    margin: '1px 4px',
                    background: isOn ? 'rgba(59,130,246,0.08)' : 'transparent',
                    transition: 'background 0.1s',
                  }}
                  onClick={() => toggleLayer(layer.id)}
                >
                  {/* Toggle indicator */}
                  <div
                    style={{
                      width: 12,
                      height: 12,
                      borderRadius: 3,
                      border: isOn
                        ? '1.5px solid #3B82F6'
                        : '1.5px solid rgba(255,255,255,0.2)',
                      background: isOn ? '#3B82F6' : 'transparent',
                      flexShrink: 0,
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      transition: 'all 0.15s',
                    }}
                  >
                    {isOn && (
                      <svg width="7" height="7" viewBox="0 0 8 8" fill="none">
                        <polyline
                          points="1,4 3,6 7,2"
                          stroke="white"
                          strokeWidth="1.5"
                          strokeLinecap="round"
                        />
                      </svg>
                    )}
                  </div>
                  <span
                    style={{
                      fontSize: 11,
                      color: isOn ? '#E2E8F0' : '#64748B',
                      flex: 1,
                      fontWeight: isOn ? 500 : 400,
                      transition: 'color 0.1s',
                    }}
                  >
                    {layer.label}
                  </span>
                  {/* Cached indicator */}
                  {isCached && (
                    <div
                      style={{
                        width: 5,
                        height: 5,
                        borderRadius: '50%',
                        background: '#22C55E',
                        flexShrink: 0,
                      }}
                      title="Tile metadata cached"
                    />
                  )}
                </div>
              );
            })}
          </div>
        ))}
      </div>

      {/* ── Identify popup (if no matching target found) ── */}
      {identifyResult && !identifyLoading && identifyResult.total_matches === 0 && (
        <div
          style={{
            position: 'absolute',
            bottom: 60,
            left: '50%',
            transform: 'translateX(-50%)',
            zIndex: 1200,
            background: 'rgba(15,23,42,0.95)',
            border: '1px solid rgba(255,255,255,0.1)',
            borderRadius: 8,
            padding: '8px 14px',
            color: '#94A3B8',
            fontSize: 12,
            backdropFilter: 'blur(8px)',
            pointerEvents: 'none',
          }}
        >
          No GEE features found at this location
        </div>
      )}
    </div>
  );
}
