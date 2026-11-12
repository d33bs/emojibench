import { useEffect, useMemo, useState } from "react";

import catalogDocument from "../../src/emojibench/data/catalog.json";
import { checkBackend } from "./api";
import GenerationPanel from "./GenerationPanel";
import StoryKitchen from "./StoryKitchen";
import "./styles.css";

type CatalogAsset = {
  id: string;
  name: string;
  category: string;
  tags: string[];
  image_uri: string;
};

const assets = catalogDocument.assets as CatalogAsset[];

function assetUrl(asset: CatalogAsset): string {
  return `/${asset.image_uri}`;
}

function escapeXml(value: string): string {
  return value
    .replaceAll("&", "&amp;")
    .replaceAll('"', "&quot;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;");
}

function normalizedPair(
  first: CatalogAsset,
  second: CatalogAsset,
): [CatalogAsset, CatalogAsset] {
  return first.id <= second.id ? [first, second] : [second, first];
}

function previewSvg(first: CatalogAsset, second: CatalogAsset): string {
  const [left, right] = normalizedPair(first, second);
  const title = escapeXml(`Mock offline preview: ${left.name} + ${right.name}`);
  return `<svg xmlns="http://www.w3.org/2000/svg" width="512" height="320" viewBox="0 0 512 320" role="img" aria-labelledby="title">
  <title id="title">${title}</title>
  <metadata>Mock offline preview. Original emojibench inputs. BSD-3-Clause license.</metadata>
  <rect width="512" height="320" rx="32" fill="#fffaf2"/>
  <circle cx="256" cy="144" r="74" fill="#ffe299" opacity="0.8"/>
  <image href="${escapeXml(assetUrl(left))}" x="48" y="48" width="200" height="200"/>
  <image href="${escapeXml(assetUrl(right))}" x="264" y="48" width="200" height="200"/>
  <path d="M246 130h20M256 120v20" stroke="#263238" stroke-width="8" stroke-linecap="round"/>
  <text x="256" y="286" text-anchor="middle" font-family="system-ui, sans-serif" font-size="20" fill="#263238">Mock offline preview · ${escapeXml(left.id)} + ${escapeXml(right.id)}</text>
</svg>`;
}

type SelectionSlotProps = {
  asset: CatalogAsset | null;
  active: boolean;
  index: number;
  onActivate: () => void;
};

function SelectionSlot({
  asset,
  active,
  index,
  onActivate,
}: SelectionSlotProps) {
  return (
    <button
      className={`selection-slot ${active ? "selection-slot--active" : ""}`}
      data-testid={`selection-${index === 0 ? "one" : "two"}`}
      type="button"
      onClick={onActivate}
      aria-label={`Choose concept ${index + 1}`}
    >
      <span className="slot-number">{index + 1}</span>
      {asset ? (
        <>
          <img src={assetUrl(asset)} alt="" />
          <span>{asset.name}</span>
        </>
      ) : (
        <span>Choose a concept</span>
      )}
    </button>
  );
}

export default function App() {
  const [query, setQuery] = useState("");
  const [selections, setSelections] = useState<
    [CatalogAsset | null, CatalogAsset | null]
  >([null, null]);
  const [activeSlot, setActiveSlot] = useState(0);
  const [backendReady, setBackendReady] = useState(false);

  useEffect(() => {
    let active = true;
    checkBackend().then((ready) => {
      if (active) {
        setBackendReady(ready);
      }
    });
    return () => {
      active = false;
    };
  }, []);

  const filteredAssets = useMemo(() => {
    const normalizedQuery = query.trim().toLowerCase();
    if (!normalizedQuery) {
      return assets;
    }
    return assets.filter((asset) =>
      [asset.id, asset.name, asset.category, ...asset.tags]
        .join(" ")
        .toLowerCase()
        .includes(normalizedQuery),
    );
  }, [query]);

  const first = selections[0];
  const second = selections[1];

  function selectAsset(asset: CatalogAsset) {
    setSelections((current) => {
      const next: [CatalogAsset | null, CatalogAsset | null] = [...current];
      next[activeSlot] = asset;
      return next;
    });
    setActiveSlot(activeSlot === 0 ? 1 : 0);
  }

  function downloadPreview() {
    if (!first || !second) {
      return;
    }
    const [left, right] = normalizedPair(first, second);
    const blob = new Blob([previewSvg(left, right)], {
      type: "image/svg+xml;charset=utf-8",
    });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `${left.id}-${right.id}-mock-preview.svg`;
    link.click();
    URL.revokeObjectURL(url);
  }

  return (
    <main>
      <header className="hero">
        <p className="eyebrow">Offline Kitchen MVP</p>
        <h1>Mix two science concepts.</h1>
        <p>
          Pick original emojibench artwork. The kitchen creates the same mock
          preview every time, with no API key or external service.
        </p>
      </header>

      <section className="workspace" aria-label="Combination workspace">
        <div className="catalog-panel">
          <label className="search-label" htmlFor="concept-search">
            Search concepts
          </label>
          <input
            id="concept-search"
            type="search"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Try cell, lab, or hero"
          />

          <div className="concept-grid" aria-live="polite">
            {filteredAssets.map((asset) => (
              <button
                className="concept-card"
                key={asset.id}
                type="button"
                onClick={() => selectAsset(asset)}
                aria-label={`Select ${asset.name}`}
              >
                <img src={assetUrl(asset)} alt="" />
                <span className="concept-name">{asset.name}</span>
                <span className="concept-category">{asset.category}</span>
              </button>
            ))}
          </div>
          {filteredAssets.length === 0 && (
            <p className="empty-state">No concepts match this search.</p>
          )}
        </div>

        <div className="kitchen-panel">
          <div className="selection-row" aria-label="Selected concepts">
            <SelectionSlot
              asset={first}
              active={activeSlot === 0}
              index={0}
              onActivate={() => setActiveSlot(0)}
            />
            <span className="plus" aria-hidden="true">
              +
            </span>
            <SelectionSlot
              asset={second}
              active={activeSlot === 1}
              index={1}
              onActivate={() => setActiveSlot(1)}
            />
          </div>

          <div className="preview-area">
            {first && second ? (
              <>
                <span className="mock-badge">Mock offline preview</span>
                <svg
                  data-testid="combination-preview"
                  viewBox="0 0 512 320"
                  role="img"
                  aria-label={`${first.name} and ${second.name} mock preview`}
                >
                  <rect width="512" height="320" rx="32" fill="#fffaf2" />
                  <circle
                    cx="256"
                    cy="144"
                    r="74"
                    fill="#ffe299"
                    opacity="0.8"
                  />
                  <image
                    href={assetUrl(normalizedPair(first, second)[0])}
                    x="48"
                    y="48"
                    width="200"
                    height="200"
                  />
                  <image
                    href={assetUrl(normalizedPair(first, second)[1])}
                    x="264"
                    y="48"
                    width="200"
                    height="200"
                  />
                  <path
                    d="M246 130h20M256 120v20"
                    stroke="#263238"
                    strokeWidth="8"
                    strokeLinecap="round"
                  />
                  <text
                    x="256"
                    y="286"
                    textAnchor="middle"
                    className="preview-label"
                  >
                    {normalizedPair(first, second)[0].id} +{" "}
                    {normalizedPair(first, second)[1].id}
                  </text>
                </svg>
                <button
                  className="download-button"
                  type="button"
                  onClick={downloadPreview}
                >
                  Download SVG
                </button>
              </>
            ) : (
              <div className="preview-placeholder">
                <span>Preview</span>
                <p>Select two concepts to make an offline combination.</p>
              </div>
            )}
          </div>

          <GenerationPanel
            backendReady={backendReady}
            firstId={first?.id ?? null}
            secondId={second?.id ?? null}
          />
        </div>
      </section>

      <StoryKitchen
        backendReady={backendReady}
        assets={assets.map((asset) => ({
          id: asset.id,
          name: asset.name,
          image_uri: asset.image_uri,
        }))}
      />

      <footer>
        Original project artwork is available under the BSD-3-Clause license. This demo
        does not use Emoji Kitchen artwork.
      </footer>
    </main>
  );
}
