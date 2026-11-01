import "./helpers/jsx-globals";
import assert from "node:assert/strict";
import { test } from "node:test";
import { createElement } from "react";
import { renderToString } from "react-dom/server";
import { Showcase } from "../src/components/showcase/showcase";

test("showcase introduces the product and keeps a direct brief entry", () => {
  const html = renderToString(createElement(Showcase));
  assert.match(html, /One piece you love/);
  assert.match(html, /href="\/start"/);
  assert.match(html, /Build my look/);
  assert.match(html, /₹1,400/);
  assert.doesNotMatch(html, /Finishing hoops/);
  for (const section of ["example", "how-it-works", "youcam", "questions"]) {
    assert.match(html, new RegExp(`id="${section}"`));
  }
});

test("showcase distinguishes illustrations, stock imagery and provider evidence", () => {
  const html = renderToString(createElement(Showcase));
  assert.match(html, /Illustrative styling example/);
  assert.match(html, /Editorial photography/);
  assert.match(html, /not a YouCam result/);
  assert.match(html, /Live-tested integration/);
  assert.match(html, /Live verification pending/);
  assert.doesNotMatch(
    html,
    /Guaranteed fit|perfect shade match|instant results/i,
  );
});

test("all eight YouCam integrations are discoverable", () => {
  const html = renderToString(createElement(Showcase));
  for (const name of [
    "Clothes",
    "Makeup",
    "Hair colour",
    "Earrings",
    "Necklace",
    "Ring",
    "Bracelet",
    "Watch",
  ]) {
    assert.ok(html.includes(name), `Missing capability: ${name}`);
  }
  assert.match(html, /aria-pressed="true"/);
  assert.match(html, /href="\/wardrobe"/);
  assert.match(html, /href="\/compare"/);
});
