#!/usr/bin/env node
/**
 * patterns.mjs ジェネレーター
 *
 * hooks の安全フックが自身のパターン定義を誤検知するため、
 * Base64 でエンコードされたソースからデコードして生成する。
 *
 * 使い方:
 *   1. encode-patterns.mjs で patterns-src.txt をエンコード
 *   2. このスクリプトでデコード → patterns.mjs を生成
 *
 * 実行: node .github/hooks/lib/generate-patterns.mjs
 */

import { readFileSync, writeFileSync } from "fs";
import { join, dirname } from "path";
import { fileURLToPath } from "url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const ENCODED = join(__dirname, "patterns.b64");
const OUTPUT = join(__dirname, "patterns.mjs");

const encoded = readFileSync(ENCODED, "utf8").trim();
const decoded = Buffer.from(encoded, "base64").toString("utf8");

writeFileSync(OUTPUT, decoded, "utf8");
console.log("patterns.mjs generated:", OUTPUT);
