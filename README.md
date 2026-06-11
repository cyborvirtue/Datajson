# Datajson

Streamlit viewer for local JSON, JSONL, and Parquet multimodal datasets.

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

- Reads local `.json`, `.jsonl`, `.ndjson`, and `.parquet` files.
- Reads a folder path as a recursive collection of `.parquet` files.
- Supports random access over JSONL records without loading the whole file into memory.
- Supports random access over Parquet rows by reading only the row group containing the current sample.
- Supports JSON roots that are either a single object, a list of samples, or a dictionary containing a sample list such as `data`, `samples`, `items`, or `records`.
- Renders ordered text and image blocks from common multimodal structures such as `messages[].content[]`.
- Falls back to recursive detection for other local JSON shapes.
- Converts Parquet image bytes and Hugging Face-style `{bytes, path}` image structs into embedded previews.
- Resolves relative images from the JSON file folder, an optional image root, and sample metadata such as `source_image_dir`.
- Shows a missing-image panel when a path is detected but the local file is unavailable.
- Provides dark and light UI themes from the sidebar.
- Lets you switch between fixed-width image previews and full-column image previews.
- Uses a reliable sample jump control: entering an index commits immediately, and the `Go to index` button forces the same state update.

## JSON recognition rules

Dataset loading is separated from sample rendering:

- `.jsonl` and `.ndjson` are read line by line with byte offsets for random sample access.
- `.json` can be a single sample, a list of samples, or an object containing a sample list such as `data`, `samples`, `items`, `records`, `instances`, `examples`, `rows`, or `annotations`.
- `.parquet` files and folders of `.parquet` files are read row by row; image bytes are converted to `data:image/...` previews when possible.

For each sample, rendering prefers conversation-like structures first, then falls back to recursive field detection:

- Conversation keys: `messages`, `conversations`, `chats`.
- Role keys: `role`, `from`, `speaker`, `author`.
- Text/content keys: `content`, `value`, `text`, `message`, `parts`, `contents`.
- Image typed items: `image`, `img`, `picture`, `photo`, `input_image`, `image_url`, `input_image_url`, `local_image`.
- Text typed items: `text`, `markdown`, `caption`, `input_text`, `output_text`.
- Image path keys include `image`, `images`, `image_path`, `image_url`, `data_url`, `data_uri`, `path`, `url`, `uri`, `src`, `local_path`, `relative_path`, `file`, `filename`, `asset_path`, `media_path`, and related variants.
- Text keys include `text`, `caption`, `prompt`, `instruction`, `question`, `answer`, `response`, `input`, `output`, `query`, `query_text`, `answer_text`, `ocr`, and `ground_truth`.

Image references are resolved from direct paths, remote URLs, embedded `data:image/...` values, and sample-level image collections such as `images`, `image_paths`, `image_urls`, `original_images`, `input_images`, `source_images`, `assets`, and `meta.images`. The parser also recognizes labels and placeholders such as `Image #2`, `image_0`, `img1`, `图片1`, `<image>`, `<image_0>`, Markdown images, and HTML `<img src="...">`. Missing local paths are still rendered as missing-image blocks.

## Project structure

```text
Datajson/
  app.py                      # Streamlit entrypoint and page orchestration
  datajson/
    config.py                 # App constants and JSON/image/text key lists
    models.py                 # Shared dataclasses for datasets and render blocks
    json_store.py             # JSON/JSONL/Parquet loading, sample collections, cached file access
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

Recent dataset paths are stored locally in `.datajson_history.json`; this file is ignored by git.

## Notes

The translation tab is intentionally not enabled yet. The rendering pipeline already isolates text blocks, so a later translation feature can translate only the current sample or selected JSON paths without changing the parser.
