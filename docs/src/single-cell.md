# Single-cell extensions

emojibench separates whimsical art from scientific evidence. This page
explains the metadata that connects a story panel to real microscopy, and
where future integrations will attach.

## Evidence categories

Every story panel caption carries an `evidence_status`:

| Status             | Meaning                                              | Requirement |
| ------------------ | ---------------------------------------------------- | ----------- |
| `observation`      | Something directly shown in a source image or dataset | References are required |
| `interpretation`   | A reasonable reading of an observation               | Say what would change the reading |
| `creative_analogy` | Playful storytelling, never scientific evidence      | Keep it clearly playful |

A generated or hand-drawn illustration is never scientific evidence. A
panel may use a whimsical image, but its caption must not claim the image
depicts a real cell unless the panel references real evidence.

## Scientific assets

An asset with `kind: scientific` must carry `scientific_metadata`
containing a `microscopy_source` record:

| Field         | Purpose                                          |
| ------------- | ------------------------------------------------ |
| `dataset`     | Source dataset name, for example `RxRx19a`       |
| `image_uri`   | Image or crop identifier inside the dataset      |
| `attribution` | Who created the source image                    |
| `license`     | License of the source image                     |
| `crop`        | Optional crop box: x, y, width, height in pixels |
| `object_id`   | Optional segmentation object identifier         |
| `dimensions`  | Source image width and height in pixels         |
| `measurements`| Optional per-object measurements                |
| `references`  | Optional scientific citations                    |

See `examples/scientific-metadata-example.json` for a metadata-only
record. The record documents the source without copying image data. The
stylized rendering and the experimental source stay separate files: a
panel links to evidence, it never replaces it.

Model validation enforces the rule: `Asset` with `kind: scientific` and a
missing or invalid `microscopy_source` fails validation.

## Future integrations

The fields above are the documented extension points. Planned links:

- OME-Zarr / OME-TIFF stores: `image_uri` will point at a plate, well,
  and pyramid level inside an OME store. `crop` and `object_id` select
  the region or label.
- CytoDataFrame / OME-Arrow tables: `object_id` joins to a row of
  per-cell features. `measurements` holds a small preview of columns.
- AnnData: `object_id` joins to an `obs` row when profiles attach.
- Source datasets stay read-only. emojibench stores references and small
  stylized renderings, never modified copies of experimental data.

## What is deliberately out of scope for now

Segmentation, feature extraction, Zarr reading, and dataset hosting are
not implemented. The models leave the hooks so these can be added without
schema changes.
