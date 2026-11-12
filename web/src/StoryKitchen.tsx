import { useState } from "react";

import { exportStory } from "./api";

type StoryAsset = {
  id: string;
  name: string;
  image_uri: string;
};

type Panel = {
  asset_id: string;
  caption: string;
  evidence_status: "observation" | "interpretation" | "creative_analogy";
  references?: string[];
};

type StoryKitchenProps = {
  backendReady: boolean;
  assets: StoryAsset[];
};

const MAX_PANELS = 5;
const MIN_PANELS = 3;

function assetUrl(asset: StoryAsset): string {
  return `/${asset.image_uri}`;
}

function emptyPanel(): Panel {
  return {
    asset_id: "",
    caption: "",
    evidence_status: "creative_analogy",
  };
}

/**
 * Story composition UI. Arrange 3-5 panels from approved assets, set
 * captions and audience, then export the story JSON through the backend.
 */
export default function StoryKitchen({
  backendReady,
  assets,
}: StoryKitchenProps) {
  const [title, setTitle] = useState("A Macrophage Saves the Day");
  const [audience, setAudience] = useState("kids");
  const [panels, setPanels] = useState<Panel[]>([
    emptyPanel(),
    emptyPanel(),
    emptyPanel(),
  ]);
  const [message, setMessage] = useState<string | null>(null);

  function updatePanel(index: number, patch: Partial<Panel>) {
    setPanels((current) =>
      current.map((panel, i) => (i === index ? { ...panel, ...patch } : panel)),
    );
  }

  async function submitStory() {
    setMessage(null);
    try {
      const exportPath = await exportStory({
        title,
        audience,
        panels: panels.map((panel) => ({
          ...panel,
          references:
            panel.evidence_status === "observation" && panel.references
              ? panel.references
              : undefined,
        })),
      });
      setMessage(`Story exported to ${exportPath}`);
    } catch (storyError) {
      setMessage(
        storyError instanceof Error
          ? storyError.message
          : "Story export failed.",
      );
    }
  }

  if (!backendReady) {
    return null;
  }

  const allPanelsReady =
    panels.length >= MIN_PANELS &&
    panels.every(
      (panel) => panel.asset_id !== "" && panel.caption.trim() !== "",
    );

  return (
    <section className="story-kitchen" aria-label="Story kitchen">
      <h2>Build a story</h2>
      <p className="story-hint">
        Arrange {MIN_PANELS} to {MAX_PANELS} panels from approved assets.
        Observation captions need a reference. Playful captions stay clearly
        playful.
      </p>

      <div className="story-meta">
        <label htmlFor="story-title">Title</label>
        <input
          id="story-title"
          type="text"
          value={title}
          onChange={(event) => setTitle(event.target.value)}
        />
        <label htmlFor="story-audience">Audience</label>
        <select
          id="story-audience"
          value={audience}
          onChange={(event) => setAudience(event.target.value)}
        >
          <option value="kids">kids</option>
          <option value="general">general</option>
          <option value="researchers">researchers</option>
        </select>
      </div>

      {panels.map((panel, index) => (
        <div className="story-panel" key={index} data-testid={`panel-${index}`}>
          <h3>Panel {index + 1}</h3>
          <label htmlFor={`panel-asset-${index}`}>Asset</label>
          <select
            id={`panel-asset-${index}`}
            value={panel.asset_id}
            onChange={(event) =>
              updatePanel(index, { asset_id: event.target.value })
            }
          >
            <option value="">Choose an asset</option>
            {assets.map((asset) => (
              <option key={asset.id} value={asset.id}>
                {asset.name}
              </option>
            ))}
          </select>

          <label htmlFor={`panel-caption-${index}`}>Caption</label>
          <input
            id={`panel-caption-${index}`}
            type="text"
            value={panel.caption}
            onChange={(event) =>
              updatePanel(index, { caption: event.target.value })
            }
            placeholder="One short sentence."
          />

          <label htmlFor={`panel-evidence-${index}`}>Evidence</label>
          <select
            id={`panel-evidence-${index}`}
            value={panel.evidence_status}
            onChange={(event) =>
              updatePanel(index, {
                evidence_status: event.target
                  .value as Panel["evidence_status"],
              })
            }
          >
            <option value="creative_analogy">creative analogy</option>
            <option value="interpretation">interpretation</option>
            <option value="observation">observation</option>
          </select>

          {panel.evidence_status === "observation" && (
            <>
              <label htmlFor={`panel-reference-${index}`}>
                Reference (required for observations)
              </label>
              <input
                id={`panel-reference-${index}`}
                type="text"
                value={panel.references?.[0] ?? ""}
                onChange={(event) =>
                  updatePanel(index, {
                    references: [event.target.value],
                  })
                }
                placeholder="Dataset, citation, or asset id."
              />
            </>
          )}

          {panel.asset_id && (
            <img
              className="story-thumb"
              src={assetUrl(
                assets.find((asset) => asset.id === panel.asset_id) ??
                  ({ id: panel.asset_id, name: "", image_uri: "" } as StoryAsset),
              )}
              alt=""
            />
          )}
        </div>
      ))}

      <div className="story-actions">
        <button
          type="button"
          disabled={panels.length <= MIN_PANELS}
          onClick={() =>
            setPanels((current) => current.slice(0, current.length - 1))
          }
        >
          Remove panel
        </button>
        <button
          type="button"
          disabled={panels.length >= MAX_PANELS}
          onClick={() => setPanels((current) => [...current, emptyPanel()])}
        >
          Add panel
        </button>
        <button
          type="button"
          className="download-button"
          disabled={!allPanelsReady}
          onClick={submitStory}
        >
          Export story
        </button>
      </div>

      {message && (
        <p className="story-message" role="status">
          {message}
        </p>
      )}
    </section>
  );
}
