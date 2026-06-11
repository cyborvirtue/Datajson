from __future__ import annotations


APP_TITLE = "Datajson"
DEFAULT_JSONL = (
    "/Users/kalami/Keyan/dllm/Work01-data收集/datapipeline/"
    "01_格式转换/Weave/weave_interleaved_en.jsonl"
)

IMAGE_EXTS = (".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".tif", ".tiff")
IMAGE_KEYS = {
    "image",
    "images",
    "img",
    "imgs",
    "photo",
    "picture",
    "pic",
    "filepath",
    "file_path",
    "image_path",
    "img_path",
    "path",
    "url",
    "uri",
    "data_url",
    "data_uri",
    "bytes",
    "filename",
    "file_name",
}
TEXT_KEYS = {
    "text",
    "caption",
    "prompt",
    "instruction",
    "question",
    "answer",
    "response",
    "content",
    "value",
    "description",
    "query",
    "title",
}
COLLECTION_KEYS = {
    "data",
    "samples",
    "items",
    "records",
    "instances",
    "examples",
    "rows",
    "annotations",
    "dataset",
}
