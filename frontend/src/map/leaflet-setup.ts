import L from 'leaflet';

// leaflet.heat and legacy plugins expect global L
if (typeof window !== 'undefined') {
  (window as any).L = L;
}

export default L;
