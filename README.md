# Datajson

Streamlit viewer for local JSON and JSONL multimodal datasets.

## Quick start

```bash
cd /Users/kalami/Keyan/dllm/Related_code/Datajson
conda env create -f environment.yml
conda activate datajson-viewer
streamlit run app.py
```

If the environment already exists:

```bash
conda activate datajson-viewer
pip install -r requirements.txt
streamlit run app.py
```

## What it does

- Reads local `.json`, `.jsonl`, and `.ndjson` files.
- Supports random access over JSONL records without loading the whole file into memory.
- Supports JSON roots that are either a single object, a list of samples, or a dictionary containing a sample list such as `data`, `samples`, `items`, or `records`.
- Renders ordered text and image blocks from common multimodal structures such as `messages[].content[]`.
- Falls back to recursive detection for other local JSON shapes.
- Resolves relative images from the JSON file folder, an optional image root, and sample metadata such as `source_image_dir`.
- Shows a missing-image panel when a path is detected but the local file is unavailable.
- Provides dark and light UI themes from the sidebar.
- Lets you switch between fixed-width image previews and full-column image previews.
- Uses a reliable sample jump control: entering an index commits immediately, and the `Go to index` button forces the same state update.

## Project structure

```text
Datajson/
  app.py                      # Streamlit entrypoint and page orchestration
  datajson/
    config.py                 # App constants and JSON/image/text key lists
    models.py                 # Shared dataclasses for datasets and render blocks
    json_store.py             # JSON/JSONL loading, sample collections, cached file access
    history.py                # Lightweight recent JSON path history
    blocks.py                 # Text/image detection, image path resolution, field flattening
    ui/
      theme.py                # Dark/light theme CSS and inline SVG icons
      sidebar.py              # Sidebar controls, display settings, sample navigation
      components.py           # Main Streamlit render components
  .streamlit/config.toml      # Streamlit theme/server defaults
  environment.yml             # Conda environment definition
  requirements.txt            # pip dependencies
```

Recent JSON paths are stored locally in `.datajson_history.json`; this file is ignored by git.

## Notes

The translation tab is intentionally not enabled yet. The rendering pipeline already isolates text blocks, so a later translation feature can translate only the current sample or selected JSON paths without changing the parser.
