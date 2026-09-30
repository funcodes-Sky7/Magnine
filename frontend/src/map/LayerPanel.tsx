import React from 'react';
import type { Layer } from '../services/api';

interface Props {
  layers: Layer[];
  visibility: Record<string, boolean>;
  opacity: Record<string, number>;
  onToggle: (id: string) => void;
  onOpacity: (id: string, v: number) => void;
  onCollapse?: () => void;
}

export default function LayerPanel({ layers, visibility, opacity, onToggle, onOpacity, onCollapse }: Props) {

  return (
    <div className="layer-panel">
      <div className="layer-panel-header">
        <span className="layer-panel-title">Data Sources</span>
        <button className="btn btn-secondary btn-sm btn-icon" onClick={onCollapse} title="Collapse">
          ›
        </button>
      </div>

      <div className="layer-list">
        {layers.map(layer => (
          <div key={layer.id} className="layer-item">
            <div className="layer-item-header">
              <input
                type="checkbox"
                className="layer-toggle"
                checked={visibility[layer.id] ?? layer.default_visible}
                onChange={() => onToggle(layer.id)}
                id={`layer-${layer.id}`}
              />
              <label className="layer-name" htmlFor={`layer-${layer.id}`} style={{ cursor: 'pointer' }}>
                {layer.name}
              </label>
              <span className={`layer-status ${layer.status}`}>{layer.status}</span>
            </div>

            <div className="layer-source">{layer.source}</div>

            {(visibility[layer.id] ?? layer.default_visible) && (
              <div className="layer-opacity-row">
                <input
                  type="range"
                  className="opacity-slider"
                  min={0} max={100}
                  value={Math.round((opacity[layer.id] ?? layer.opacity) * 100)}
                  onChange={e => onOpacity(layer.id, Number(e.target.value) / 100)}
                />
                <span className="opacity-label">
                  {Math.round((opacity[layer.id] ?? layer.opacity) * 100)}%
                </span>
              </div>
            )}
          </div>
        ))}
      </div>

      <div style={{ padding: '8px 12px', borderTop: '1px solid var(--border-light)', fontSize: 10, color: 'var(--text-muted)', lineHeight: 1.4 }}>
        DEMO DATA — For system demonstration only. Not certified geological reserve data.
      </div>
    </div>
  );
}
