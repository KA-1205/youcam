import "./helpers/jsx-globals";
import assert from "node:assert/strict";
import { test } from "node:test";
import { createElement } from "react";
import { renderToString } from "react-dom/server";
import { PhotoCapture } from "../src/components/photo-capture";

test("photo capture shows guidance and requires consent before selecting a file", () => {
  const out = renderToString(createElement(PhotoCapture, { capability: "CLOTHES_V4" }));
  assert.match(out, /only you visible/i);
  assert.match(out, /shoulders/i);
  assert.match(out, /disabled/);
  assert.match(out, /18 or older|18\+/i);
});

test("photo capture names its capability and never claims an upload happens", () => {
  const out = renderToString(createElement(PhotoCapture, { capability: "MAKEUP" }));
  assert.match(out, /MAKEUP/);
  assert.match(out, /never sent/i);
});
